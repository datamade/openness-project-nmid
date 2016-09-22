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
                  period.filing_date
                FROM camp_fin_candidate AS candidate
                JOIN camp_fin_filing AS filing
                  USING(entity_id)
                JOIN camp_fin_filingperiod AS period
                  ON filing.filing_period_id = period.id
                JOIN camp_fin_campaign AS campaign
                  ON filing.campaign_id = campaign.id
                JOIN camp_fin_office AS office
                  ON campaign.office_id = office.id
                WHERE filing.date_added >= '2010-01-01'
                  AND period.exclude_from_cascading = FALSE
                  AND period.regular_filing_period_id IS NULL
                ORDER BY candidate.id, period.filing_date DESC
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
        
        entity_id = context['object'].entity_id
        
        summed_filings = ''' 
            SELECT 
              SUM(f.total_contributions) + \
                SUM(COALESCE(f.total_supplemental_contributions, 0)) AS total_contributions,
              SUM(f.total_expenditures) AS total_expenditures,
              SUM(COALESCE(f.total_loans, 0)) AS total_loans,
              SUM(COALESCE(f.total_unpaid_debts, 0)) AS total_unpaid_debts,
              SUM(f.closing_balance) AS closing_balance,
              fp.filing_date
            FROM camp_fin_filing AS f
            JOIN camp_fin_filingperiod AS fp
              ON f.filing_period_id = fp.id
            WHERE f.entity_id = %s
              AND fp.exclude_from_cascading = FALSE
              AND fp.regular_filing_period_id IS NULL
              AND fp.filing_date >= '2010-01-01'
            GROUP BY fp.filing_date
            ORDER BY fp.filing_date
        '''

        cursor = connection.cursor()
        
        cursor.execute(summed_filings, [entity_id])
        
        columns = [c[0] for c in cursor.description]
        filing_tuple = namedtuple('Filings', columns)
        
        summed_filings = [filing_tuple(*r) for r in cursor]

        balance_trend = []
        debt_trend = []

        for filing in summed_filings:
            filing_date = filing.filing_date
            date_array = [filing_date.year, filing_date.month, filing_date.day]
            debts = (-1 * filing.total_unpaid_debts)
            balance_trend.append([filing.closing_balance, *date_array])
            debt_trend.append([debts, *date_array])
        
        all_filings = ''' 
            SELECT 
              f.total_contributions + \
                COALESCE(f.total_supplemental_contributions, 0) AS total_contributions,
              f.total_expenditures,
              f.total_loans,
              f.total_unpaid_debts,
              f.closing_balance,
              f.opening_balance,
              fp.filing_date::date, 
              fp.initial_date,
              f.campaign_id,
              fp.due_date::date
            FROM camp_fin_filing AS f
            JOIN camp_fin_filingperiod AS fp
              ON f.filing_period_id = fp.id
            WHERE f.entity_id = %s
              AND fp.exclude_from_cascading = FALSE
              AND fp.regular_filing_period_id IS NULL
              AND fp.filing_date >= '2010-01-01'
            ORDER BY fp.filing_date
        '''
        
        cursor.execute(all_filings, [entity_id])
        
        columns = [c[0] for c in cursor.description]
        filing_tuple = namedtuple('Filings', columns)
        
        all_filings = [filing_tuple(*r) for r in cursor]
        
        grouper = lambda x: x.campaign_id
        sorted_filings = sorted(all_filings, key=grouper)
        
        donation_trend = []
        expend_trend = []
        
        for campaign_id, filings in itertools.groupby(sorted_filings, key=grouper):
            
            filings = list(filings)
            
            for index, filing in enumerate(filings):
                filing_duration = (filing.filing_date - filing.initial_date).days / 7 
                donation_rate = (filing.total_contributions - filing.total_loans) / filing_duration
                expenditure_rate = (-1 * filing.total_expenditures) / filing_duration
                
                begin_date_array = [filing.initial_date.year, 
                                    filing.initial_date.month, 
                                    filing.initial_date.day]
                
                end_date_array = [filing.due_date.year,
                                  filing.due_date.month,
                                  filing.due_date.day]

                end_date = end_date_array
                
                donation_trend.append([begin_date_array, end_date_array, donation_rate])
                
                expend_trend.append([begin_date_array, end_date_array, expenditure_rate])
        
        donation_trend = self.stackTrends(donation_trend)
        expend_trend = self.stackTrends(expend_trend)
        
        context['latest_filing'] = all_filings[-1]
        context['balance_trend'] = balance_trend
        context['donation_trend'] = donation_trend
        context['expend_trend'] = expend_trend
        context['debt_trend'] = debt_trend

        return context
    
    def stackTrends(self, trend):
        trend = sorted(trend)
        
        stacked_trend = []
        for begin, end, rate in trend:
            if not stacked_trend:
                stacked_trend.append((rate, begin))
                stacked_trend.append((rate, end))
            
            elif begin == stacked_trend[-1][1]:
                stacked_trend.append((rate, begin))
                stacked_trend.append((rate, end))
            
            elif begin > stacked_trend[-1][1]:
                previous_rate, previous_end = stacked_trend[-1]
                stacked_trend.append((previous_rate, begin))
                stacked_trend.append((rate, begin))
                stacked_trend.append((rate, end))
            
            elif begin < stacked_trend[-1][1]:
                previous_rate, previous_end = stacked_trend.pop()
                stacked_trend.append((previous_rate, begin))
                stacked_trend.append((rate + previous_rate, begin))
                
                if end < previous_end:
                    stacked_trend.append((rate + previous_rate, end))
                    stacked_trend.append((previous_rate, end))
                    stacked_trend.append((previous_rate, previous_end))
                    
                elif end > previous_end:
                    stacked_trend.append((rate + previous_rate, previous_end))
                    stacked_trend.append((rate, previous_end))
                    stacked_trend.append((rate, end))
                else:
                    stacked_trend.append((rate + previous_rate, end))
        
        flattened_trend = []
        dupe_date_flag = False
        previous_date = None
        

        for i, point in enumerate(stacked_trend):
            rate, date = point
            flattened_trend.append([rate, *date])

        return flattened_trend


class CandidateDetail(CommitteeDetailBaseView):
    template_name = "camp_fin/candidate-detail.html"
    model = Candidate
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_loans = ''' 
            SELECT 
              loan.*,
              status.*
            FROM camp_fin_candidate AS c
            JOIN camp_fin_filing AS f
              USING(entity_id)
            JOIN camp_fin_loan AS loan
              ON f.id = loan.filing_id
            JOIN current_loan_status AS status
              ON loan.id = status.loan_id
            WHERE c.id = %s
        '''
        
        cursor = connection.cursor()
        
        cursor.execute(current_loans, [context['object'].id])
        
        columns = [c[0] for c in cursor.description]
        loan_tuple = namedtuple('Loans', columns)
        
        context['loans'] = [loan_tuple(*r) for r in cursor]
        
        return context

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
                  period.filing_date
                FROM camp_fin_pac AS pac
                JOIN camp_fin_filing AS filing
                  USING(entity_id)
                JOIN camp_fin_filingperiod AS period
                  ON filing.filing_period_id = period.id
                WHERE filing.date_added >= '2010-01-01'
                  AND period.exclude_from_cascading = FALSE
                  AND period.regular_filing_period_id IS NULL
                ORDER BY pac.id, period.filing_date DESC
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
    
    # def get_queryset(self):
    #     transactions = ''' 
    #         select c.full_name, c.id, s.* from camp_fin_filing as f join (select t.filing_id, t.id, amount, full_name, tt.description, tt.contribution from camp_fin_transaction as t join camp_fin_transactiontype as tt on t.transaction_type_id = tt.id union select lt.filing_id, lt.id, lt.amount, l.full_name, ltt.description, FALSE as contribution from camp_fin_loantransaction as lt join camp_fin_loantransactiontype as ltt on lt.transaction_type_id = ltt.id join camp_fin_loan as l on lt.loan_id = l.id where ltt.description = 'Payment') as s on f.id = s.filing_id join camp_fin_candidate as c on f.entity_id = c.entity_id where c.id = 815 and s.contribution = FALSE;
    #     '''

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
                        d.full_name AS related_entity_name, 
                        '/candidates/' || d.slug || '/' AS related_entity_url, 
                        t.search_name 
                      FROM camp_fin_treasurer AS t 
                      JOIN camp_fin_address AS a 
                        ON t.address_id = a.id 
                      JOIN camp_fin_state AS s 
                        ON a.state_id = s.id 
                      JOIN camp_fin_campaign AS m 
                        ON t.id = m.treasurer_id 
                      JOIN camp_fin_candidate AS d 
                        ON m.candidate_id = d.id 
                      
                      UNION 
                      
                      SELECT 
                        t.full_name, 
                        a.street, 
                        a.city, 
                        s.postal_code AS state, 
                        a.zipcode, 
                        p.name AS related_entity_name, 
                        '/committees/' || p.slug || '/' AS related_entity_url, 
                        t.search_name 
                      FROM camp_fin_treasurer AS t 
                      JOIN camp_fin_address AS a 
                        ON t.address_id = a.id 
                      JOIN camp_fin_state AS s 
                        ON a.state_id = s.id 
                      JOIN camp_fin_pac AS p 
                        ON t.id = p.treasurer_id
                    ) AS s 
                    WHERE search_name @@ plainto_tsquery('english', %s)
                '''
            
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
