from collections import namedtuple
from datetime import datetime
import csv

from django.views.generic import ListView, DetailView, TemplateView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse, StreamingHttpResponse
from django.db import connection
from django.utils import timezone
from django.utils.text import slugify

from rest_framework import viewsets, filters, renderers
from rest_framework.response import Response

from camp_fin.models import Transaction, Candidate, PAC, Entity
from camp_fin.api_parts import (TransactionSerializer, TopMoneySerializer,
                                SearchCSVRenderer, DataTablesPagination,
                                TransactionCSVRenderer)

from pages.models import Page

TWENTY_TEN = timezone.make_aware(datetime(2010, 1, 1))


class Echo(object):
    def write(self, value):
        return value


class PaginatedList(ListView):
    
    per_page = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        paginator = Paginator(context['object_list'], self.per_page)

        page = self.request.GET.get('page')
        try:
            context['object_list'] = paginator.page(page)
        except PageNotAnInteger:
            context['object_list'] = paginator.page(1)
        except EmptyPage:
            context['object_list'] = paginator.page(paginator.num_pages)
        
        return context

class TransactionDetail(DetailView):
    model = Transaction
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['entity'] = None

        if context['transaction'].filing.entity.candidate_set.all():
            context['entity'] = context['transaction'].filing.entity.candidate_set.first()
            context['office'] = context['transaction'].filing.campaign.office
        elif context['transaction'].filing.entity.pac_set.all():
            context['entity'] = context['transaction'].filing.entity.pac_set.first()
            context['office'] = None

        context['entity_type'] = context['entity']._meta.model_name

        if context['transaction'].transaction_type.description.lower().endswith('contribution'):
            context['transaction_type'] = 'contribution'
        else:
            context['transaction_type'] = 'expenditure'
        
        filing = context['object'].filing
        mountain_time = timezone.get_current_timezone()
        date_closed = mountain_time.normalize(filing.date_closed.astimezone(mountain_time))
        
        query_params = '{camp_id}_{filing_id}_{year}_{month}_{day}_{hour}{minute}{second}.pdf'
        
        camp_id = filing.campaign_id
        if not camp_id:
            camp_id = 0

        query_params = query_params.format(camp_id=camp_id,
                                           filing_id=filing.id,
                                           year=date_closed.year,
                                           month=date_closed.month,
                                           day=date_closed.day,
                                           hour=date_closed.hour,
                                           minute=date_closed.minute,
                                           second=date_closed.second)

        context['sos_link'] = 'https://www.cfis.state.nm.us/docs/FPReports/{}'.format(query_params)

        return context


class TransactionDownloadViewSet(viewsets.ViewSet):
    '''
    Base viewset for returning bulk downloads of contributions and expenditures
    as CSV.
    '''
    serializer_class = TransactionSerializer
    renderer_classes = (TransactionCSVRenderer,)
    contribution = True

    allowed_methods = ['GET']

    def get_entity_id(self, request):
        '''
        Retrieve the entity ID from a request. Can be tied to either the 'candidate_id'
        or 'pac_id' param, depending on the type of request.
        '''
        if request.GET.get('candidate_id'):
            candidate_id = request.GET.get('candidate_id')
            candidate = Candidate.objects.get(id=candidate_id)
            self.entity_name = candidate.full_name
            entity = candidate.entity
            return entity.id

        elif request.GET.get('pac_id'):
            pac_id = request.GET.get('pac_id')
            pac = PAC.objects.get(id=pac_id)
            self.entity_name = pac.name
            entity = pac.entity
            return entity.id

        else:
            # Bulk download
            self.entity_name = 'bulk'
            return None

    def transaction_query(self, entity_id=None):
        '''
        Return a query corresponding to the request, either for transactions by
        candidate/PAC or for all transactions.
        '''
        if self.contribution is True:
            contribution_bool = 'TRUE'
            subj_type = 'recipient'
        else:
            contribution_bool = 'FALSE'
            subj_type = 'spender'

        base_query = '''
            SELECT
              transaction.*,
              tt.description AS transaction_type,
              entity.*,
              fp.filing_date,
              fp.description AS filing_name
            FROM camp_fin_transaction AS transaction
            JOIN camp_fin_transactiontype AS tt
              ON transaction.transaction_type_id = tt.id
            JOIN camp_fin_filing AS f
              ON transaction.filing_id = f.id
            JOIN camp_fin_filingperiod AS fp
              ON f.filing_period_id = fp.id
            JOIN (
              SELECT
                  entity_id AS {subj_type}_entity_id,
                  transaction_subject,
                  entity_type AS {subj_type}_entity_type
              FROM (
                SELECT
                  entity_id,
                  full_name AS transaction_subject,
                  'candidate' AS entity_type
                FROM camp_fin_candidate
                UNION
                SELECT
                  entity_id,
                  name AS transaction_subject,
                  'pac' AS entity_type
                  FROM camp_fin_pac
              ) AS all_entities
            ) AS entity
              ON f.entity_id = entity.{subj_type}_entity_id
            WHERE tt.contribution = {contribution_bool}
              AND fp.filing_date >= '2010-01-01'
        '''.format(contribution_bool=contribution_bool,
                   subj_type=subj_type)

        if entity_id:
            base_query += '''
                AND entity_id = %s
            '''

        base_query += '''ORDER BY transaction.received_date'''

        return base_query

    def list(self, request):
        '''
        Generate the response to a request.
        '''
        self.entity_id = self.get_entity_id(request)

        if self.contribution is True:
            ttype = 'contributions'
        else:
            ttype = 'expenditures'

        query = self.transaction_query(self.entity_id)

        cursor = connection.cursor()

        if self.entity_id:
            cursor.execute(query, [self.entity_id])
        else:
            cursor.execute(query)

        header = [c[0] for c in cursor.description]

        streaming_buffer = Echo()
        writer = csv.writer(streaming_buffer)
        writer.writerow(header)

        response = StreamingHttpResponse((writer.writerow(row) for row in iterate_cursor(header, cursor)),
                                        content_type='text/csv')

        # Add appropriate filename and header for CSV response
        filename = '{0}-{1}-{2}.csv'.format(ttype,
                                            slugify(self.entity_name),
                                            timezone.now().isoformat())

        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

        return response

class TransactionBaseViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    default_filter = {}
    queryset = Transaction.objects.filter(filing__date_added__gte=TWENTY_TEN)
    filter_backends = (filters.OrderingFilter,)
    
    ordering_fields = ('last_name', 'amount', 'received_date', 'description')
    
    allowed_methods = ['GET']

    def get_queryset(self):
        
        queryset = super().get_queryset()

        if self.default_filter:
            queryset = queryset.filter(**self.default_filter)

        candidate_id = self.request.query_params.get('candidate_id')
        pac_id = self.request.query_params.get('pac_id')
        
        if candidate_id:
            queryset = queryset.filter(filing__campaign__candidate__id=candidate_id)
        elif pac_id:
            queryset = queryset.filter(filing__entity__pac__id=pac_id)
        
        else:
            self.entity_name = None
            return []
        

        if self.request.query_params.get('format') == 'csv':
            
            entity = queryset.first().filing.entity
            
            if entity.candidate_set.first():
                self.entity_name = entity.candidate_set.first().full_name
            
            elif entity.pac_set.first():
                self.entity_name = entity.pac_set.first().name

        return queryset.order_by('-received_date')
    

class TopMoneyView(viewsets.ViewSet):
    
    def list(self, request):
        
        cursor = connection.cursor()
        
        query = ''' 
            SELECT * FROM (
              SELECT 
                DENSE_RANK() 
                  OVER (
                    PARTITION BY year 
                    ORDER BY amount DESC
                  ) AS rank, *
              FROM (
                SELECT 
                  SUM(transaction.amount) AS amount,
                  NULL AS latest_date,
                  transaction.name_prefix, 
                  transaction.first_name, 
                  transaction.middle_name, 
                  transaction.last_name,
                  transaction.suffix,
                  transaction.company_name,
                  election_season.year 
                FROM camp_fin_transaction AS transaction 
                JOIN camp_fin_transactiontype AS tt 
                  ON transaction.transaction_type_id = tt.id 
                JOIN camp_fin_filing AS f 
                  ON transaction.filing_id = f.id 
                JOIN camp_fin_campaign AS c 
                  ON f.campaign_id = c.id 
                JOIN camp_fin_electionseason AS election_season
                  ON c.election_season_id = election_season.id
                WHERE tt.contribution = %s 
                  AND year >= '2010' 
                GROUP BY 
                  transaction.name_prefix, 
                  transaction.first_name, 
                  transaction.middle_name, 
                  transaction.last_name,
                  transaction.suffix,
                  transaction.company_name,
                  year 
                ORDER BY SUM(amount) DESC
              ) AS ranked_list 
              ORDER BY year DESC, amount DESC
            ) AS election_groups 
            WHERE rank < 11
        '''
        
        if self.request.GET.get('entity_type') == 'pac':
            query = ''' 
                SELECT *, NULL AS year FROM (
                  SELECT 
                    DENSE_RANK() 
                      OVER (
                        ORDER BY amount DESC
                      ) AS rank, *
                  FROM (
                    SELECT 
                      SUM(transaction.amount) AS amount, 
                      MAX(transaction.received_date) AS latest_date,
                      transaction.name_prefix, 
                      transaction.first_name, 
                      transaction.middle_name, 
                      transaction.last_name,
                      transaction.suffix,
                      transaction.company_name
                    FROM camp_fin_transaction AS transaction 
                    JOIN camp_fin_transactiontype AS tt 
                      ON transaction.transaction_type_id = tt.id 
                    JOIN camp_fin_filing AS f 
                      ON transaction.filing_id = f.id 
                    WHERE tt.contribution = %s 
                      AND transaction.received_date >= '2010-01-01'
                    GROUP BY 
                      transaction.name_prefix, 
                      transaction.first_name, 
                      transaction.middle_name, 
                      transaction.last_name,
                      transaction.suffix,
                      transaction.company_name
                    ORDER BY SUM(amount) DESC
                  ) AS ranked_list 
                  ORDER BY amount DESC
                ) AS election_groups 
                WHERE rank < 11
            '''

        cursor.execute(query, [self.contribution])
        
        columns = [c[0] for c in cursor.description]
        transaction_tuple = namedtuple('Transaction', columns)
        
        objects =  [transaction_tuple(*r) for r in cursor]
        
        serializer = TopMoneySerializer(objects, many=True)

        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        cursor = connection.cursor()
        
        query = ''' 
            SELECT * FROM (
              SELECT 
                DENSE_RANK() 
                  OVER (
                    PARTITION BY year 
                    ORDER BY amount DESC
                  ) AS rank, *
              FROM (
                SELECT 
                  SUM(transaction.amount) AS amount, 
                  MAX(transaction.received_date) AS latest_date,
                  transaction.name_prefix, 
                  transaction.first_name, 
                  transaction.middle_name, 
                  transaction.last_name,
                  transaction.suffix,
                  transaction.company_name,
                  election_season.year 
                FROM camp_fin_transaction AS transaction 
                JOIN camp_fin_transactiontype AS tt 
                  ON transaction.transaction_type_id = tt.id 
                JOIN camp_fin_filing AS f 
                  ON transaction.filing_id = f.id 
                JOIN camp_fin_campaign AS c 
                  ON f.campaign_id = c.id 
                JOIN camp_fin_candidate as candidate
                  ON c.candidate_id = candidate.id
                JOIN camp_fin_electionseason AS election_season
                  ON c.election_season_id = election_season.id
                WHERE tt.contribution = %s 
                  AND candidate.id = %s
                  AND transaction.received_date >= '2010-01-01' 
                GROUP BY 
                  transaction.name_prefix, 
                  transaction.first_name, 
                  transaction.middle_name, 
                  transaction.last_name,
                  transaction.suffix,
                  transaction.company_name,
                  election_season.year 
                ORDER BY SUM(amount) DESC
              ) AS ranked_list 
              ORDER BY year DESC, amount DESC
            ) AS election_groups 
            WHERE rank < 11
        '''
        if self.request.GET.get('entity_type') == 'pac':
            query = ''' 
                SELECT *, NULL AS year FROM (
                  SELECT 
                    DENSE_RANK() 
                      OVER (
                        ORDER BY amount DESC
                      ) AS rank, *
                  FROM (
                    SELECT 
                      SUM(transaction.amount) AS amount, 
                      MAX(transaction.received_date) AS latest_date,
                      transaction.name_prefix, 
                      transaction.first_name, 
                      transaction.middle_name, 
                      transaction.last_name,
                      transaction.suffix,
                      transaction.company_name
                    FROM camp_fin_transaction AS transaction 
                    JOIN camp_fin_transactiontype AS tt 
                      ON transaction.transaction_type_id = tt.id 
                    JOIN camp_fin_filing AS f 
                      ON transaction.filing_id = f.id 
                    JOIN camp_fin_pac AS pac
                      ON f.entity_id = pac.entity_id
                    WHERE tt.contribution = %s 
                      AND pac.id = %s
                      AND transaction.received_date >= '2010-01-01' 
                    GROUP BY 
                      transaction.name_prefix, 
                      transaction.first_name, 
                      transaction.middle_name, 
                      transaction.last_name,
                      transaction.suffix,
                      transaction.company_name
                    ORDER BY SUM(amount) DESC
                  ) AS ranked_list 
                  ORDER BY amount DESC
                ) AS election_groups 
                WHERE rank < 11
            '''
        
        cursor.execute(query, [self.contribution, pk])
        
        columns = [c[0] for c in cursor.description]
        transaction_tuple = namedtuple('Transaction', columns)
        
        objects =  [transaction_tuple(*r) for r in cursor]
        
        serializer = TopMoneySerializer(objects, many=True)

        return Response(serializer.data)

class TopEarnersBase(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        with connection.cursor() as cursor:

            # Top earners
            cursor.execute(''' 
              SELECT * FROM (
                SELECT 
                  dense_rank() OVER (ORDER BY new_funds DESC) AS rank, * 
                FROM (
                  SELECT 
                    MAX(COALESCE(c.slug, p.slug)) AS slug, 
                    MAX(COALESCE(c.full_name, p.name)) AS name, 
                    SUM(t.amount) AS new_funds, 
                    (array_agg(f.closing_balance ORDER BY f.id DESC))[1] AS current_funds, 
                    CASE WHEN p.id IS NULL 
                      THEN 'Candidate' 
                      ELSE 'PAC' 
                    END AS committee_type 
                    FROM camp_fin_transaction AS t 
                    JOIN camp_fin_transactiontype AS tt 
                      ON t.transaction_type_id = tt.id 
                    JOIN camp_fin_filing AS f 
                      ON t.filing_id = f.id 
                    LEFT JOIN camp_fin_pac AS p 
                      ON f.entity_id = p.entity_id 
                    LEFT JOIN camp_fin_candidate AS c 
                      ON f.entity_id = c.entity_id 
                    WHERE tt.contribution = TRUE 
                      AND t.received_date >= (NOW() - INTERVAL '90 days')
                    GROUP BY c.id, p.id
                  ) AS s 
                WHERE name NOT ILIKE '%public election fund%'
                  OR name NOT ILIKE '%department of finance%'
                ORDER BY new_funds DESC
                LIMIT 10
              ) AS s
            ''')

            columns = [c[0] for c in cursor.description]
            transaction_tuple = namedtuple('Transaction', columns)
            top_earners_objects = [transaction_tuple(*r) for r in cursor]
        
        context['top_earners_objects'] = top_earners_objects

        return context

class PagesMixin(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            page = Page.objects.get(path=self.page_path)
            context['page'] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            context['page'] = None
        
        return context


def iterate_cursor(header, cursor):
    yield header
    
    for row in cursor:
        yield row
