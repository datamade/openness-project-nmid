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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        per_page = self.request.GET.get('per_page', '25')

        paginator = Paginator(context['object_list'], per_page)

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
    
    ordering_fields = ('last_name', 'amount', 'received_date')

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
        
        return queryset

class TopMoneyView(viewsets.ViewSet):
    
    def list(self, request):
        
        cursor = connection.cursor()
        
        query = ''' 
            SELECT
              SUM(amount) AS amount,
              MAX(received_date) AS last_date,
              name_prefix,
              first_name,
              middle_name,
              last_name,
              suffix,
              company_name
            FROM camp_fin_transaction AS transaction
            JOIN camp_fin_transactiontype AS type
              ON transaction.transaction_type_id = type.id
            WHERE type.contribution = %s
            GROUP BY 
              name_prefix,
              first_name,
              middle_name,
              last_name,
              suffix,
              company_name
            HAVING(MAX(received_date) >= '01-01-2010')
            ORDER BY amount DESC
            LIMIT 100
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
            SELECT
              SUM(amount) AS amount,
              MAX(received_date) AS last_date,
              name_prefix,
              first_name,
              middle_name,
              last_name,
              suffix,
              company_name
            FROM camp_fin_transaction AS transaction
            JOIN camp_fin_transactiontype AS type
              ON transaction.transaction_type_id = type.id
            JOIN camp_fin_filing AS filing
              ON transaction.filing_id = filing.id
            JOIN camp_fin_entity AS entity
              ON filing.entity_id = entity.id
            WHERE type.contribution = %s
              AND entity.id = %s
            GROUP BY 
              name_prefix,
              first_name,
              middle_name,
              last_name,
              suffix,
              company_name
            HAVING(MAX(received_date) >= '01-01-2010')
            ORDER BY amount DESC
            LIMIT 25
        '''
        
        entity_type = self.request.query_params.get('entity_type', 'candidate')
        
        # TODO: Return 404 if the thing is not found
        if entity_type == 'candidate':
            candidate = Candidate.objects.get(id=pk)
            entity_id = candidate.entity_id
        elif entity_type == 'pac':
            pac = PAC.objects.get(id=pk)
            entity_id = pac.entity_id
        
        else:
            return Response({'error': 'object not found'}, status=404)



        cursor.execute(query, [self.contribution, entity_id])
        
        columns = [c[0] for c in cursor.description]
        transaction_tuple = namedtuple('Transaction', columns)
        
        objects =  [transaction_tuple(*r) for r in cursor]
        
        serializer = TopMoneySerializer(objects, many=True)

        return Response(serializer.data)
