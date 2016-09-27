from collections import namedtuple
from datetime import datetime

from django.views.generic import ListView, DetailView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import JsonResponse
from django.db import connection
from django.utils import timezone

from rest_framework import viewsets, filters
from rest_framework.response import Response

from camp_fin.models import Transaction, Candidate, PAC
from camp_fin.api_parts import TransactionSerializer, TopMoneySerializer

TWENTY_TEN = timezone.make_aware(datetime(2010, 1, 1))

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

        return context

class TransactionBaseViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    default_filter = {}
    queryset = Transaction.objects.filter(filing__date_added__gte=TWENTY_TEN)
    filter_backends = (filters.OrderingFilter,)
    
    ordering_fields = ('last_name', 'amount', 'received_date', 'description')

    def get_queryset(self):
        
        queryset = super().get_queryset()

        if self.default_filter:
            queryset = queryset.filter(**self.default_filter)
        else:
            queryset = queryset.all()

        candidate_id = self.request.query_params.get('candidate_id')
        pac_id = self.request.query_params.get('pac_id')
        if candidate_id:
            queryset = queryset.filter(filing__campaign__candidate__id=candidate_id)
        if pac_id:
            queryset = queryset.filter(filing__entity__pac__id=pac_id)
        
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
