import itertools
from collections import namedtuple, OrderedDict

from django.views.generic import ListView, TemplateView, DetailView
from django.http import HttpResponseNotFound
from django.db import transaction, connection

from rest_framework import serializers, viewsets, filters, generics, metadata
from rest_framework.response import Response

from .models import Candidate, Office, Transaction, Campaign, Filing, PAC
from .base_views import PaginatedList

class IndexView(TemplateView):
    template_name = 'index.html'

class CandidateList(PaginatedList):
    template_name = "camp_fin/candidate-list.html"

    def get_queryset(self, **kwargs):
        cursor = connection.cursor()
        
        self.order_by = self.request.GET.get('order_by', 'closing_balance')
        self.sort_order = self.request.GET.get('sort_order', 'desc')

        cursor.execute(''' 
            SELECT * FROM (
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
              ORDER BY candidate.id, filing.date_added desc
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

class CandidateDetail(DetailView):
    template_name = "camp_fin/candidate-detail.html"
    model = Candidate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        latest_filing = context['candidate'].entity.filing_set\
                                            .order_by('-filing_period__filing_date')\
                                            .first()
        
        context['latest_filing'] = latest_filing
        
        return context

class CommitteeList(PaginatedList):
    template_name = 'camp_fin/committee-list.html'

    def get_queryset(self, **kwargs):
        cursor = connection.cursor()
        
        self.order_by = self.request.GET.get('order_by', 'closing_balance')
        self.sort_order = self.request.GET.get('sort_order', 'desc')

        cursor.execute(''' 
            SELECT * FROM (
              SELECT DISTINCT ON (pac.id) 
                pac.*, 
                filing.closing_balance, 
                filing.date_added AS filing_date
              FROM camp_fin_pac AS pac 
              JOIN camp_fin_filing AS filing 
                USING(entity_id)
              ORDER BY pac.id, filing.date_added desc
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

class CommitteeDetail(DetailView):
    template_name = "camp_fin/committee-detail.html"
    model = PAC

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        latest_filing = context['pac'].entity.filing_set\
                                            .order_by('-filing_period__filing_date')\
                                            .first()
        
        context['latest_filing'] = latest_filing
        
        return context

class TransactionDetail(DetailView):
    model = Transaction
    
    def get_template_name(self, **kwargs):
        
        
        return [template_name]

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

class ContributionDetail(TransactionDetail):
    template_name = 'camp_fin/contribution-detail.html'

class ExpenditureDetail(TransactionDetail):
    template_name = 'camp_fin/expenditure-detail.html'

class CandidateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Candidate
        fields = '__all__'

class PACSerializer(serializers.ModelSerializer):

    class Meta:
        model = PAC
        fields = '__all__'

class FilingField(serializers.RelatedField):

    def to_representation(self, value):
        
        if value.entity.pac_set.all():
            serializer = PACSerializer(value.entity.pac_set.first())
        
        elif value.entity.candidate_set.all():
            serializer = CandidateSerializer(value.entity.candidate_set.first())

        return serializer.data


class TransactionSerializer(serializers.ModelSerializer):
    transaction_type = serializers.StringRelatedField(read_only=True)
    full_name = serializers.StringRelatedField(read_only=True)
    transaction_subject = FilingField(read_only=True)

    class Meta:
        model = Transaction
        
        fields = (
            'id',
            'amount', 
            'received_date', 
            'date_added', 
            'check_number',
            'memo',
            'description',
            'transaction_type',
            'name_prefix',
            'first_name',
            'middle_name',
            'last_name',
            'suffix',
            'company_name',
            'full_name',
            'address',
            'city',
            'state',
            'zipcode',
            'full_address',
            'country',
            'occupation',
            'expenditure_for_certified_candidate',
            'transaction_subject'
        )


class TransactionBaseViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    default_filter = {}
    filter_backends = (filters.OrderingFilter,)
    
    ordering_fields = ('last_name', 'amount', 'received_date')

    def get_queryset(self):

        if self.default_filter:
            queryset = Transaction.objects.filter(**self.default_filter)
        else:
            queryset = Transaction.objects.all()

        candidate_id = self.request.query_params.get('candidate_id')
        pac_id = self.request.query_params.get('pac_id')
        if candidate_id:
            queryset = queryset.filter(filing__campaign__candidate__id=candidate_id)
        if pac_id:
            queryset = queryset.filter(filing__entity__pac__id=pac_id)
        
        return queryset

class TransactionViewSet(TransactionBaseViewSet):
    pass

class ContributionViewSet(TransactionBaseViewSet):
    default_filter = {'transaction_type__contribution': True}


class ExpenditureViewSet(TransactionBaseViewSet):
    default_filter = {'transaction_type__contribution': False}

class TopMoneySerializer(serializers.Serializer):
    name_prefix = serializers.CharField()
    first_name = serializers.CharField()
    middle_name = serializers.CharField()
    last_name = serializers.CharField()
    suffix = serializers.CharField()
    company_name = serializers.CharField()
    amount = serializers.CharField()
    last_date = serializers.DateTimeField()

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

class TopDonorsView(TopMoneyView):
    contribution = True

class TopExpensesView(TopMoneyView):
    contribution = False

