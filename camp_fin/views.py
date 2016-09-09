import itertools
from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta

from django.views.generic import ListView, TemplateView, DetailView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponseNotFound
from django.db import transaction, connection
from django.utils import timezone

from rest_framework import serializers, viewsets, filters, generics, metadata
from rest_framework.response import Response

from .models import Candidate, Office, Transaction, Campaign, Filing, PAC, \
    LoanTransaction
from .base_views import PaginatedList, TransactionDetail, TransactionBaseViewSet, \
    TopMoneyView
from .api_parts import CandidateSerializer, PACSerializer, TransactionSerializer, \
    TransactionSearchSerializer, CandidateSearchSerializer, PACSearchSerializer, \
    LoanTransactionSerializer

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
                  ORDER BY o.amount DESC LIMIT 10
              ) AS x;
            ''')

            columns = [c[0] for c in cursor.description]
            transaction_tuple = namedtuple('Transaction', columns)
            transaction_objects = [transaction_tuple(*r) for r in cursor]

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
                    ORDER BY pac.id, filing.date_added desc
                  ) AS pac
                ) AS s
                ORDER BY {0} {1}
                LIMIT 10
            '''.format(self.order_by, self.sort_order))

            columns = [c[0] for c in cursor.description]
            pac_tuple = namedtuple('PAC', columns)
            pac_objects = [pac_tuple(*r) for r in cursor]

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
                    ORDER BY candidate.id, filing.date_added DESC
                  ) AS candidates
                ) AS s
                ORDER BY {0} {1}
                LIMIT 10
            '''.format(self.order_by, self.sort_order))

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
            SELECT MAX(o.received_date)
            FROM camp_fin_transaction AS o
            JOIN camp_fin_transactiontype AS tt
            ON o.transaction_type_id = tt.id
            JOIN camp_fin_filing AS filing
            ON o.filing_id = filing.id
            WHERE tt.contribution = TRUE
            AND o.received_date <= '$[today]';
            '''
            cursor.execute(count_query)
            row = cursor.fetchone()
            max_date = row[0].date()

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
                  ORDER BY o.received_date ASC
              ) as z;
            '''

            days_donations = []

            if ('from' in self.request.GET) and ('to' in self.request.GET):
                start_date_str = self.request.GET.get('from')
                self.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() + timedelta(days=1)

                end_date_str = self.request.GET.get('to')
                self.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() + timedelta(days=2)

                print(self.start_date)
                print(self.end_date)

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
        context['start_date'] = self.start_date
        context['end_date'] = self.end_date
        context['donation_count'] = self.donation_count
        context['donation_sum'] = self.donation_sum
        return context

class AboutView(TemplateView):
    template_name = 'about.html'

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

class CandidateDetail(DetailView):
    template_name = "camp_fin/candidate-detail.html"
    model = Candidate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_filings = context['candidate'].entity.filing_set\
                                          .filter(date_added__gte=TWENTY_TEN)\
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

class CommitteeDetail(DetailView):
    template_name = "camp_fin/committee-detail.html"
    model = PAC

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        latest_filing = context['pac'].entity.filing_set\
                                             .filter(date_added__gte=TWENTY_TEN)\
                                             .order_by('-filing_period__filing_date')\
                                             .first()

        context['latest_filing'] = latest_filing

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
}

class SearchAPIView(viewsets.ViewSet):
    def list(self, request):
        table_names = request.GET.getlist('table_name')
        term = request.GET.get('term')

        if not term:
            return Response({'error': 'term is required'}, status=400)

        if not table_names:
            table_names = [
                'candidate',
                'pac',
                'contribution',
                'expenditure'
            ]

        response = {}

        for table in table_names:
            query = '''
                SELECT * FROM camp_fin_{}
                WHERE search_name @@ plainto_tsquery('english', %s)
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
                      AND filing.date_added >= '01-01-2010'
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
                      AND filing.date_added >= '01-01-2010'
                '''

            serializer = SERIALIZER_LOOKUP[table]

            cursor = connection.cursor()
            cursor.execute(query, [term])

            columns = [c[0] for c in cursor.description]
            result_tuple = namedtuple(table, columns)

            objects =  [result_tuple(*r) for r in cursor]

            serializer = serializer(objects, many=True)

            response[table] = serializer.data

        return Response(response)
