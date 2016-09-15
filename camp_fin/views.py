import itertools
from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta
import time

from django.views.generic import ListView, TemplateView, DetailView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponseNotFound
from django.db import transaction, connection
from django.utils import timezone
from django.core.urlresolvers import reverse_lazy

from rest_framework import serializers, viewsets, filters, generics, metadata
from rest_framework.response import Response

from .models import Candidate, Office, Transaction, Campaign, Filing, PAC, \
    LoanTransaction
from .base_views import PaginatedList, TransactionDetail, TransactionBaseViewSet, \
    TopMoneyView
from .api_parts import CandidateSerializer, PACSerializer, TransactionSerializer, \
    TransactionSearchSerializer, CandidateSearchSerializer, PACSearchSerializer, \
    LoanTransactionSerializer, TreasurerSearchSerializer, DataTablesPagination

TWENTY_TEN = timezone.make_aware(datetime(2010, 1, 1))

class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute('''
              SELECT * FROM (
                SELECT
                    DENSE_RANK() OVER (ORDER BY amount DESC) AS rank,
                    o.*,
                    tt.description AS transaction_type,
                    CASE WHEN
                      pac.name IS NULL OR TRIM(pac.name) = ''
                    THEN
                      candidate.full_name
                    ELSE pac.name
                    END AS transaction_subject,
                    pac.slug AS pac_slug,
                    candidate.slug AS candidate_slug
                  FROM camp_fin_transaction AS o
                  JOIN camp_fin_transactiontype AS tt
                    ON o.transaction_type_id = tt.id
                  JOIN camp_fin_filing AS filing
                    ON o.filing_id = filing.id
                  JOIN camp_fin_entity AS entity
                    ON filing.entity_id = entity.id
                  LEFT JOIN camp_fin_pac AS pac
                    ON entity.id = pac.entity_id
                  LEFT JOIN camp_fin_candidate AS candidate
                    ON entity.id = candidate.entity_id
                  WHERE tt.contribution = TRUE
                    AND o.received_date >= '2010-01-01'
                  ORDER BY o.amount DESC LIMIT 10
              ) AS x;
            ''')

            columns = [c[0] for c in cursor.description]
            transaction_tuple = namedtuple('Transaction', columns)
            transaction_objects = [transaction_tuple(*r) for r in cursor]

            cursor.execute('''
                SELECT * FROM (
                  SELECT
                    DENSE_RANK() OVER (ORDER BY closing_balance DESC) AS rank,
                    pac.*
                  FROM (
                    SELECT DISTINCT ON (pac.id)
                      pac.*,
                      filing.closing_balance,
                      filing.date_added AS filing_date
                    FROM camp_fin_pac AS pac
                    JOIN camp_fin_filing AS filing
                      USING(entity_id)
                    WHERE filing.date_added >= '2010-01-01'
                    ORDER BY pac.id, filing.date_added desc
                  ) AS pac
                ) AS s
                ORDER BY closing_balance DESC
                LIMIT 10
            ''')

            columns = [c[0] for c in cursor.description]
            pac_tuple = namedtuple('PAC', columns)
            pac_objects = [pac_tuple(*r) for r in cursor]

            cursor.execute('''
                SELECT * FROM (
                  SELECT
                    DENSE_RANK() OVER (ORDER BY closing_balance DESC) AS rank,
                    candidates.*
                  FROM (
                    SELECT DISTINCT ON (candidate.id)
                      candidate.*,
                      campaign.committee_name,
                      campaign.county_id,
                      campaign.district_id,
                      campaign.division_id,
                      office.description AS office_name,
                      filing.closing_balance,
                      filing.date_last_amended
                    FROM camp_fin_candidate AS candidate
                    JOIN camp_fin_filing AS filing
                      USING(entity_id)
                    JOIN camp_fin_campaign AS campaign
                      ON filing.campaign_id = campaign.id
                    JOIN camp_fin_office AS office
                      ON campaign.office_id = office.id
                    WHERE filing.date_added >= '2010-01-01'
                    ORDER BY candidate.id, filing.date_added DESC
                  ) AS candidates
                ) AS s
                LIMIT 10
            ''')

            columns = [c[0] for c in cursor.description]
            candidate_tuple = namedtuple('Candidate', columns)
            candidate_objects = [candidate_tuple(*r) for r in cursor]

            context = super().get_context_data(**kwargs)
            context['transaction_objects'] = transaction_objects
            context['pac_objects'] = pac_objects
            context['candidate_objects'] = candidate_objects
            return context

class DonationsView(PaginatedList):
    template_name = 'camp_fin/donations.html'

    def get_queryset(self, **kwargs):
        with connection.cursor() as cursor:
            today = datetime.now().date()

            count_query = '''
            SELECT MAX(t.received_date)
            FROM camp_fin_transaction AS t
            JOIN camp_fin_transactiontype AS tt
              ON t.transaction_type_id = tt.id
            WHERE tt.contribution = TRUE
              AND t.received_date <= NOW()
            '''
            cursor.execute(count_query)
            row = cursor.fetchone()
            max_date = row[0].date()

            self.order_by = self.request.GET.get('order_by', 'received_date')
            self.sort_order = self.request.GET.get('sort_order', 'asc')

            query = '''
            SELECT * FROM (
                SELECT
                    DENSE_RANK() OVER (ORDER BY amount DESC) AS rank,
                    o.*,
                    tt.description AS transaction_type,
                    CASE WHEN
                      pac.name IS NULL OR TRIM(pac.name) = ''
                    THEN
                      candidate.full_name
                    ELSE pac.name
                    END AS transaction_subject,
                    pac.slug AS pac_slug,
                    candidate.slug AS candidate_slug
                  FROM camp_fin_transaction AS o
                  JOIN camp_fin_transactiontype AS tt
                    ON o.transaction_type_id = tt.id
                  JOIN camp_fin_filing AS filing
                    ON o.filing_id = filing.id
                  JOIN camp_fin_entity AS entity
                    ON filing.entity_id = entity.id
                  LEFT JOIN camp_fin_pac AS pac
                    ON entity.id = pac.entity_id
                  LEFT JOIN camp_fin_candidate AS candidate
                    ON entity.id = candidate.entity_id
                  WHERE tt.contribution = TRUE
                  AND o.received_date BETWEEN %s and %s
                  ORDER BY {0} {1}
              ) as z
            '''.format(self.order_by, self.sort_order)

            days_donations = []

            if ('from' in self.request.GET) and ('to' in self.request.GET):
                start_date_str = self.request.GET.get('from')
                self.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() + timedelta(days=1)

                end_date_str = self.request.GET.get('to')
                self.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() + timedelta(days=2)

                cursor.execute(query, [self.start_date, self.end_date])
                days_donations = list(cursor)

                # Reset variables.
                self.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                self.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            else:
                self.end_date = max_date + timedelta(days=2)
                self.start_date = max_date + timedelta(days=1)

                # Find dates for main query.
                while len(days_donations) == 0:
                    cursor.execute(count_query, [self.start_date, self.end_date])
                    days_donations = list(cursor)

                    self.end_date = self.end_date - timedelta(days=1)
                    self.start_date = self.start_date - timedelta(days=1)

                # Run main query.
                cursor.execute(query, [self.start_date, self.end_date])
                days_donations = list(cursor)

                self.start_date = self.start_date - timedelta(days=1)
                self.end_date = self.start_date

            columns = [c[0] for c in cursor.description]
            result_tuple = namedtuple('Transaction', columns)
            donation_objects = [result_tuple(*r) for r in days_donations]

            self.donation_count = len(donation_objects)
            self.donation_sum = sum([d.amount for d in donation_objects])
            return donation_objects

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['sort_order'] = self.sort_order
        context['toggle_order'] = 'desc'

        if self.sort_order.lower() == 'desc':
            context['toggle_order'] = 'asc'

        context['order_by'] = self.order_by

        context['start_date'] = self.start_date
        context['end_date'] = self.end_date
        context['donation_count'] = self.donation_count
        context['donation_sum'] = self.donation_sum
        return context

class SearchView(TemplateView):
    template_name = 'camp_fin/search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['term'] = self.request.GET.get('term')
        context['table_name'] = self.request.GET.getlist('table_name')

        return context

class CandidateList(PaginatedList):
    template_name = "camp_fin/candidate-list.html"

    def get_queryset(self, **kwargs):
        cursor = connection.cursor()

        self.order_by = self.request.GET.get('order_by', 'closing_balance')
        self.sort_order = self.request.GET.get('sort_order', 'desc')

        cursor.execute('''
            SELECT * FROM (
              SELECT
                DENSE_RANK() OVER (ORDER BY closing_balance DESC) AS rank,
                candidates.*
              FROM (
                SELECT DISTINCT ON (candidate.id)
                  candidate.*,
                  campaign.committee_name,
                  campaign.county_id,
                  campaign.district_id,
                  campaign.division_id,
                  office.description AS office_name,
                  filing.closing_balance,
                  filing.date_last_amended
                FROM camp_fin_candidate AS candidate
                JOIN camp_fin_filing AS filing
                  USING(entity_id)
                JOIN camp_fin_campaign AS campaign
                  ON filing.campaign_id = campaign.id
                JOIN camp_fin_office AS office
                  ON campaign.office_id = office.id
                WHERE filing.date_added >= '2010-01-01'
                ORDER BY candidate.id, filing.date_added desc
              ) AS candidates
            ) AS s
            ORDER BY {0} {1}
        '''.format(self.order_by, self.sort_order))

        columns = [c[0] for c in cursor.description]
        candidate_tuple = namedtuple('Candidate', columns)

        return [candidate_tuple(*r) for r in cursor]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['sort_order'] = self.sort_order

        context['toggle_order'] = 'desc'
        if self.sort_order.lower() == 'desc':
            context['toggle_order'] = 'asc'

        context['order_by'] = self.order_by

        return context

class CommitteeDetailBaseView(DetailView):
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_filings = context['object'].entity.filing_set\
                                       .filter(date_added__gte=TWENTY_TEN)\
                                       .filter(final=False)\
                                       .filter(filing_period__exclude_from_cascading=False)\
                                       .order_by('filing_period__filing_date')


        balance_trend = [[ f.closing_balance,
                           f.filing_period.filing_date.year,
                           f.filing_period.filing_date.month,
                           f.filing_period.filing_date.day]
                           for f in all_filings]
        
        donation_trend = [[f.total_contributions,
                           f.filing_period.filing_date.year,
                           f.filing_period.filing_date.month,
                           f.filing_period.filing_date.day]
                           for f in all_filings]
        
        expend_trend = [[  (-1*f.total_expenditures),
                           f.filing_period.filing_date.year,
                           f.filing_period.filing_date.month,
                           f.filing_period.filing_date.day]
                           for f in all_filings]
    
        context['latest_filing'] = all_filings.last()
        context['balance_trend'] = balance_trend
        context['donation_trend'] = donation_trend
        context['expend_trend'] = expend_trend
        
        return context


class CandidateDetail(CommitteeDetailBaseView):
    template_name = "camp_fin/candidate-detail.html"
    model = Candidate
    
class CommitteeDetail(CommitteeDetailBaseView):
    template_name = "camp_fin/committee-detail.html"
    model = PAC

class CommitteeList(PaginatedList):
    template_name = 'camp_fin/committee-list.html'

    def get_queryset(self, **kwargs):
        cursor = connection.cursor()

        self.order_by = self.request.GET.get('order_by', 'closing_balance')
        self.sort_order = self.request.GET.get('sort_order', 'desc')

        cursor.execute('''
            SELECT * FROM (
              SELECT
                DENSE_RANK() OVER (ORDER BY closing_balance DESC) AS rank,
                pac.*
              FROM (
                SELECT DISTINCT ON (pac.id)
                  pac.*,
                  filing.closing_balance,
                  filing.date_added AS filing_date
                FROM camp_fin_pac AS pac
                JOIN camp_fin_filing AS filing
                  USING(entity_id)
                WHERE filing.date_added >= '2010-01-01'
                ORDER BY pac.id, filing.date_added desc
              ) AS pac
            ) AS s
            ORDER BY {0} {1}
        '''.format(self.order_by, self.sort_order))

        columns = [c[0] for c in cursor.description]
        pac_tuple = namedtuple('PAC', columns)

        return [pac_tuple(*r) for r in cursor]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['sort_order'] = self.sort_order

        context['toggle_order'] = 'desc'
        if self.sort_order.lower() == 'desc':
            context['toggle_order'] = 'asc'

        context['order_by'] = self.order_by

        return context



class ContributionDetail(TransactionDetail):
    template_name = 'camp_fin/contribution-detail.html'

class ExpenditureDetail(TransactionDetail):
    template_name = 'camp_fin/expenditure-detail.html'

class TransactionViewSet(TransactionBaseViewSet):
    pass

class ContributionViewSet(TransactionBaseViewSet):
    default_filter = {
        'transaction_type__contribution': True,
        'filing__date_added__gte': TWENTY_TEN
    }
    serializer_class = TransactionSerializer

class ExpenditureViewSet(TransactionBaseViewSet):
    default_filter = {
        'transaction_type__contribution': False,
        'filing__date_added__gte': TWENTY_TEN
    }
    serializer_class = TransactionSerializer

class TopDonorsView(TopMoneyView):
    contribution = True

class TopExpensesView(TopMoneyView):
    contribution = False

class LoanViewSet(TransactionBaseViewSet):
    queryset = LoanTransaction.objects.filter(transaction_date__gte=TWENTY_TEN)
    serializer_class = LoanTransactionSerializer

SERIALIZER_LOOKUP = {
    'candidate': CandidateSearchSerializer,
    'pac': PACSearchSerializer,
    'contribution': TransactionSearchSerializer,
    'expenditure': TransactionSearchSerializer,
    'treasurer': TreasurerSearchSerializer,
}

class SearchAPIView(viewsets.ViewSet):
    
    def list(self, request):
        
        table_names = request.GET.getlist('table_name')
        term = request.GET.get('term')
        datatype = request.GET.get('datatype')
        
        limit = request.GET.get('limit', 50)
        offset = request.GET.get('offset', 0)
        
        order_by_col = None
        sort_order = 'ASC'

        if request.GET.get('length'):
            limit = request.GET['length']
        
        if request.GET.get('start'):
            offset = request.GET['start']
        
        if request.GET.get('order[0][column]'):
            col_idx = request.GET['order[0][column]']
            order_by_col = request.GET['columns[' + str(col_idx) + '][data]']
            
            sort_order = request.GET['order[0][dir]']
        
        if not term:
            return Response({'error': 'term is required'}, status=400)

        if not table_names:
            table_names = [
                'candidate',
                'pac',
                'contribution',
                'expenditure',
                'treasurer',
            ]

        response = {}

        for table in table_names:

            if table == 'pac':
                query = '''
                    SELECT * FROM (
                      SELECT DISTINCT ON (pac.id)
                        pac.*, 
                        treasurer.full_name AS treasurer_name 
                      FROM camp_fin_pac AS pac
                      JOIN camp_fin_treasurer AS treasurer
                        ON pac.treasurer_id = treasurer.id
                      JOIN camp_fin_filing AS filing
                        ON filing.entity_id = pac.entity_id
                      WHERE pac.search_name @@ plainto_tsquery('english', %s)
                        AND filing.date_added >= '2010-01-01'
                      ORDER BY pac.id
                    ) AS s
                '''.format(table)
            
            if table == 'candidate':
                # TODO: finish this query
                query = '''
                    SELECT * FROM (
                      SELECT DISTINCT ON (candidate.id)
                        candidate.*,
                        campaign.committee_name,
                        county.name AS county_name,
                        election.year AS election_year,
                        party.name AS party_name,
                        office.description AS office_name,
                        officetype.description AS office_type,
                        district.name AS district_name,
                        division.name AS division_name
                      FROM camp_fin_candidate AS candidate
                      JOIN camp_fin_campaign AS campaign
                        ON candidate.id = campaign.candidate_id
                      JOIN camp_fin_electionseason AS election
                        ON campaign.election_season_id = election.id
                      JOIN camp_fin_politicalparty AS party
                        ON campaign.political_party_id = party.id
                      LEFT JOIN camp_fin_county AS county
                        ON campaign.county_id = county.id
                      JOIN camp_fin_office AS office
                        ON campaign.office_id = office.id
                      JOIN camp_fin_officetype AS officetype
                        ON office.office_type_id = officetype.id
                      LEFT JOIN camp_fin_district AS district
                        ON campaign.district_id = district.id
                      LEFT JOIN camp_fin_division AS division
                        ON campaign.division_id = division.id
                      WHERE candidate.search_name @@ plainto_tsquery('english', %s)
                        AND campaign.date_added >= '2010-01-01'
                      ORDER BY candidate.id, election.year DESC
                    ) AS s
                '''.format(table)

            if table == 'contribution':
                query = '''
                    SELECT
                      o.*,
                      tt.description AS transaction_type,
                      CASE WHEN
                        pac.name IS NULL OR TRIM(pac.name) = ''
                      THEN
                        candidate.full_name
                      ELSE pac.name
                      END AS transaction_subject,
                      pac.slug AS pac_slug,
                      candidate.slug AS candidate_slug
                    FROM camp_fin_transaction AS o
                    JOIN camp_fin_transactiontype AS tt
                      ON o.transaction_type_id = tt.id
                    JOIN camp_fin_filing AS filing
                      ON o.filing_id = filing.id
                    JOIN camp_fin_entity AS entity
                      ON filing.entity_id = entity.id
                    LEFT JOIN camp_fin_pac AS pac
                      ON entity.id = pac.entity_id
                    LEFT JOIN camp_fin_candidate AS candidate
                      ON entity.id = candidate.entity_id
                    WHERE o.search_name @@ plainto_tsquery('english', %s)
                      AND tt.contribution = TRUE
                      AND o.received_date >= '2010-01-01'
                '''
            elif table == 'expenditure':
                query = '''
                    SELECT
                      o.*,
                      tt.description AS transaction_type,
                      CASE WHEN
                        pac.name IS NULL OR TRIM(pac.name) = ''
                      THEN
                        candidate.full_name
                      ELSE pac.name
                      END AS transaction_subject,
                      pac.slug AS pac_slug,
                      candidate.slug AS candidate_slug
                    FROM camp_fin_transaction AS o
                    JOIN camp_fin_transactiontype AS tt
                      ON o.transaction_type_id = tt.id
                    JOIN camp_fin_filing AS filing
                      ON o.filing_id = filing.id
                    JOIN camp_fin_entity AS entity
                      ON filing.entity_id = entity.id
                    LEFT JOIN camp_fin_pac AS pac
                      ON entity.id = pac.entity_id
                    LEFT JOIN camp_fin_candidate AS candidate
                      ON entity.id = candidate.entity_id
                    WHERE o.search_name @@ plainto_tsquery('english', %s)
                      AND tt.contribution = FALSE
                      AND o.received_date >= '2010-01-01'
                '''
            
            elif table == 'treasurer':
                query = ''' 
                    SELECT * FROM (
                      SELECT 
                        t.full_name,
                        a.street,
                        a.city,
                        s.postal_code AS state,
                        a.zipcode,
                        CASE WHEN 
                          p.name = '' OR p.name IS NULL
                        THEN
                          d.full_name
                        ELSE
                          p.name
                        END AS related_entity_name,
                        CASE WHEN
                          p.id IS NULL
                        THEN
                          '{0}' || d.slug || '/'
                        ELSE
                          '{1}' || p.slug || '/'
                        END AS related_entity_url
                      FROM camp_fin_treasurer AS t
                      JOIN camp_fin_address AS a
                        ON t.address_id = a.id
                      JOIN camp_fin_state AS s
                        ON a.state_id = s.id
                      LEFT JOIN camp_fin_campaign AS m
                        ON t.id = m.treasurer_id
                      LEFT JOIN camp_fin_candidate AS d
                        ON m.candidate_id = d.id
                      LEFT JOIN camp_fin_pac AS p
                        ON t.id = p.treasurer_id
                      WHERE t.search_name @@ plainto_tsquery('english', %s)
                        AND m.date_added >= '2010-01-01'
                    ) AS s
                    WHERE related_entity_name IS NOT NULL
                '''.format(reverse_lazy('candidate-list'), reverse_lazy('committee-list'))
            
            if order_by_col:
                query = ''' 
                    {0} ORDER BY {1} {2}
                '''.format(query, order_by_col, sort_order)
            
            serializer = SERIALIZER_LOOKUP[table]

            cursor = connection.cursor()
            cursor.execute(query, [term])

            columns = [c[0] for c in cursor.description]
            result_tuple = namedtuple(table, columns)
            
            objects =  [result_tuple(*r) for r in cursor]
            
            paginator = DataTablesPagination()

            page = paginator.paginate_queryset(objects, self.request, view=self)
            
            serializer = serializer(page, many=True)
            
            meta = OrderedDict([
                ('total_rows', paginator.count),
                ('limit', limit),
                ('offset', offset),
                ('recordsTotal', paginator.count),
                ('recordsFiltered', limit),
                ('draw', request.GET.get('draw', 0))
            ])

            response[table] = OrderedDict([
                ('meta', meta),
                ('objects', serializer.data),
            ])
        
        return Response(response)
