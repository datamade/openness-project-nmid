import itertools
from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta
import time
import csv
from urllib.parse import urlencode

from django.views.generic import ListView, TemplateView, DetailView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponseNotFound, HttpResponse, StreamingHttpResponse
from django.db import transaction, connection, connections
from django.utils import timezone
from django.core.urlresolvers import reverse_lazy
from django.utils.text import slugify
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator

from dateutil.rrule import rrule, MONTHLY

from rest_framework import serializers, viewsets, filters, generics, metadata, \
    renderers
from rest_framework.response import Response

from pages.models import Page

from .models import Candidate, Office, Transaction, Campaign, Filing, PAC, \
    LoanTransaction
from .base_views import PaginatedList, TransactionDetail, TransactionBaseViewSet, \
    TopMoneyView
from .api_parts import CandidateSerializer, PACSerializer, TransactionSerializer, \
    TransactionSearchSerializer, CandidateSearchSerializer, PACSearchSerializer, \
    LoanTransactionSerializer, TreasurerSearchSerializer, DataTablesPagination, \
    TransactionCSVRenderer, SearchCSVRenderer
from .templatetags.helpers import format_money, get_transaction_verb

TWENTY_TEN = timezone.make_aware(datetime(2010, 1, 1))

class AboutView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            page = Page.objects.get(path='/about/')
            context['page'] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            page = None
        
        return context


class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
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
                    MAX(f.closing_balance) AS current_funds, 
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
            
            # Largest donations
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
                    AND o.received_date >= (NOW() - interval '1 year')
                    AND company_name NOT ILIKE '%public election fund%'
                    AND company_name NOT ILIKE '%department of finance%'
                  ORDER BY o.amount DESC
              ) AS x
              WHERE rank <= 5
            ''')

            columns = [c[0] for c in cursor.description]
            transaction_tuple = namedtuple('Transaction', columns)
            transaction_objects = [transaction_tuple(*r) for r in cursor]
            
            # Committees
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
            
            # Top candidates
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
            context['top_earners_objects'] = top_earners_objects
            context['transaction_objects'] = transaction_objects
            context['pac_objects'] = pac_objects
            context['candidate_objects'] = candidate_objects
            
            try:
                page = Page.objects.get(path='/')
                context['page'] = page
                for blob in page.blobs.all():
                    context[blob.context_name] = blob.text
            except Page.DoesNotExist:
                page = None
            
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
                    AND company_name NOT ILIKE '%%public election fund%%'
                    AND company_name NOT ILIKE '%%department of finance%%'
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
        
        seo = {}
        seo.update(settings.SITE_META)
        
        start_date = self.start_date.strftime('%B %-d, %Y')
        end_date = self.end_date.strftime('%B %-d, %Y')
        count = '{:,}'.format(self.donation_count)
        total = format_money(self.donation_sum)
        
        fmt_args = {
            'start_date': start_date,
            'count': count,
            'total': total,
            'end_date': end_date,
        }
        
        if start_date != end_date:
            seo['title'] = 'Donations between {start_date} and {end_date} - The Openness Project'.format(**fmt_args)
            seo['site_desc'] = '{count} donations between {start_date} and {end_date} totalling {total}'.format(**fmt_args)
        
        else:
            seo['title'] = 'Donations on {start_date} - The Openness Project'.format(**fmt_args)
            seo['site_desc'] = '{count} donations on {start_date} totalling {total}'.format(**fmt_args)


        context['seo'] = seo

        return context

class SearchView(TemplateView):
    template_name = 'camp_fin/search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['term'] = self.request.GET.get('term')
        context['table_name'] = self.request.GET.getlist('table_name')
        
        seo = {}
        seo.update(settings.SITE_META)

        seo['title'] = "Search for '{}' - The Openness Project".format(context['term'])
        seo['site_desc'] = 'Search for candidates, committees and donors in New Mexico'
        
        context['seo'] = seo

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
        
        try:
            page = Page.objects.get(path='/candidates/')
            context['page'] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            page = None
        
        seo = {}
        seo.update(settings.SITE_META)

        seo['title'] = 'Candidates - The Openness Project'
        seo['site_desc'] = 'Candidates in New Mexico'

        context['seo'] = seo
        
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
        
        try:
            page = Page.objects.get(path='/committees/')
            context['page'] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            page = None
        
        seo = {}
        seo.update(settings.SITE_META)

        seo['title'] = 'PACs - The Openness Project'
        seo['site_desc'] = 'PACs in New Mexico'

        context['seo'] = seo

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
              SUM(f.opening_balance) AS opening_balance,
              SUM(f.total_debt_carried_forward) AS debt_carried_forward,
              fp.filing_date,
              MIN(fp.initial_date) AS initial_date
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
        
        first_opening_balance = summed_filings[0].opening_balance
        first_debt = summed_filings[0].debt_carried_forward
        first_initial_date = [summed_filings[0].initial_date.year,
                              summed_filings[0].initial_date.month,
                              summed_filings[0].initial_date.day]
        balance_trend.insert(0, [first_opening_balance, *first_initial_date])
        debt_trend.insert(0, [first_debt, *first_initial_date])

        all_filings = ''' 
            SELECT 
              contributions.amount AS contribution_amount,
              expenditures.amount AS expenditure_amount,
              COALESCE(contributions.month, expenditures.month) AS month
            FROM contributions_by_month AS contributions
            JOIN expenditures_by_month AS expenditures
              ON contributions.entity_id = expenditures.entity_id
              AND contributions.month = expenditures.month
            WHERE (contributions.entity_id = %s OR expenditures.entity_id = %s)
              AND (contributions.month >= '2009-10-01' OR expenditures.month >= '2009-10-01')
            ORDER BY month
        '''
        
        cursor.execute(all_filings, [entity_id, entity_id])
        
        columns = [c[0] for c in cursor.description]
        amount_tuple = namedtuple('Amount', columns)
        
        amounts = [amount_tuple(*r) for r in cursor]
        
        contributions_lookup = {r.month.date(): r.contribution_amount for r in amounts}
        expenditures_lookup = {r.month.date(): r.expenditure_amount for r in amounts}
        
        all_months = list(contributions_lookup.keys()) + list(expenditures_lookup.keys())
        start_month, end_month = min(all_months), max(all_months)
        
        donation_trend = []
        expend_trend = []
        
        for month in rrule(freq=MONTHLY, dtstart=start_month, until=end_month):
            
            replacements = {'month': month.month - 1}

            if replacements['month'] < 1:
                replacements['month'] = 12
                replacements['year'] = month.year - 1
            
            begin_date = month.replace(**replacements)

            begin_date_array = [begin_date.year, 
                                begin_date.month, 
                                begin_date.day]
            
            end_date_array = [month.year,
                              month.month,
                              month.day]
            
            contribution_amount = contributions_lookup.get(month.date(), 0)
            expenditure_amount = expenditures_lookup.get(month.date(), 0)
            donation_trend.append([begin_date_array, end_date_array, contribution_amount])

            expend_trend.append([begin_date_array, end_date_array, (-1 * expenditure_amount)])


        donation_trend = self.stackTrends(donation_trend)
        expend_trend = self.stackTrends(expend_trend)
        
        context['latest_filing'] = context['object'].entity.filing_set.order_by('-filing_period__filing_date').first()
        context['balance_trend'] = balance_trend
        context['donation_trend'] = donation_trend
        context['expend_trend'] = expend_trend
        context['debt_trend'] = debt_trend

        return context
    
    def stackTrends(self, trend):
        # trend = sorted(trend)
        
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
        
        seo = {}
        seo.update(settings.SITE_META)
        
        first_name = context['object'].first_name
        last_name = context['object'].last_name

        seo['title'] = '{0} {1} - The Openness Project'.format(first_name,
                                                               last_name)
        seo['site_desc'] = 'Candidate information for {0} {1}'.format(first_name,
                                                                      last_name)

        context['seo'] = seo
        
        latest_campaign = context['latest_filing'].campaign
        sos_link = 'https://www.cfis.state.nm.us/media/CandidateReportH.aspx?es={es}&ot={ot}&o={o}&c={c}'
        sos_link = sos_link.format(es=latest_campaign.election_season.id,
                                   ot=latest_campaign.office.office_type.id,
                                   o=latest_campaign.office.id,
                                   c=latest_campaign.candidate_id)
        
        context['sos_link'] = sos_link

        return context

class CommitteeDetail(CommitteeDetailBaseView):
    template_name = "camp_fin/committee-detail.html"
    model = PAC

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        seo = {}
        seo.update(settings.SITE_META)
        
        seo['title'] = '{0} - The Openness Project'.format(context['object'].name)
        seo['site_desc'] = "Information about '{0}' in New Mexico".format(context['object'].name)

        context['seo'] = seo
        
        context['sos_link'] = 'https://www.cfis.state.nm.us/media/PACReport.aspx?p={}'.format(context['object'].entity_id)
        
        return context

class ContributionDetail(TransactionDetail):
    template_name = 'camp_fin/contribution-detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        seo = {}
        seo.update(settings.SITE_META)

        transaction_verb = get_transaction_verb(context['object'].transaction_type.description)
        contributor = context['object'].full_name
        amount = format_money(context['object'].amount)
        
        if hasattr(context['entity'], 'name'):
            recipient = context['entity'].name
        else:
            recipient = '{0} {1}'.format(context['entity'].first_name, 
                                         context['entity'].last_name)

        seo['title'] = '{0} {1} to {2}'.format(contributor, 
                                               transaction_verb, 
                                               recipient)
        
        seo['site_desc'] = '{0} {1} {2} to {3}'.format(contributor, 
                                                       transaction_verb,
                                                       amount,
                                                       recipient)

        context['seo'] = seo
        
        return context

class ExpenditureDetail(TransactionDetail):
    template_name = 'camp_fin/expenditure-detail.html'

class TransactionViewSet(TransactionBaseViewSet):
    serializer_class = TransactionSerializer
    renderer_classes = (renderers.JSONRenderer, TransactionCSVRenderer)
    
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        
        if request.GET.get('format') == 'csv':
            
            if self.default_filter['transaction_type__contribution']:
                ttype = 'contributions'
            else:
                ttype = 'expenditures'
            
            if not self.entity_name:
                response = HttpResponse('Use /api/bulk/{}/ to get bulk downloads'.format(ttype))
                response.status_code = 400

            else:
                filename = '{0}-{1}-{2}.csv'.format(ttype,
                                                    slugify(self.entity_name), 
                                                    timezone.now().isoformat())
                
                response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

        return response

class ContributionViewSet(TransactionViewSet):
    default_filter = {
        'transaction_type__contribution': True,
        'filing__date_added__gte': TWENTY_TEN
    }

class ExpenditureViewSet(TransactionViewSet):
    default_filter = {
        'transaction_type__contribution': False,
        'filing__date_added__gte': TWENTY_TEN
    }


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
    renderer_classes = (renderers.JSONRenderer, SearchCSVRenderer)
    
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
            
            meta = OrderedDict()

            if not request.GET.get('format') == 'csv':
                paginator = DataTablesPagination()

                page = paginator.paginate_queryset(objects, self.request, view=self)
                
                serializer = serializer(page, many=True)
                
                objects = serializer.data

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
                ('objects', objects),
            ])
        
        return Response(response)
    
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        
        if request.GET.get('format') == 'csv':
            
            term = request.GET['term']

            filename = '{0}-{1}.zip'.format(slugify(term), 
                                            timezone.now().isoformat())
            
            response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

        return response


class TopEarnersView(PaginatedList):
    template_name = 'camp_fin/top-earners.html'
    per_page = 100

    def get_queryset(self):
        
        interval = self.request.GET.get('interval', 30)
        
        if int(interval) > 0:
            where_clause = "AND t.received_date >= (NOW() - INTERVAL '%s days')"
        else:
            where_clause = "AND t.received_date >= '2010-01-01'"


        query = ''' 
            SELECT * FROM (
              SELECT 
                dense_rank() OVER (ORDER BY new_funds DESC) AS rank, * 
              FROM (
                SELECT 
                  MAX(COALESCE(c.slug, p.slug)) AS slug, 
                  MAX(COALESCE(c.full_name, p.name)) AS name, 
                  SUM(t.amount) AS new_funds, 
                  MAX(f.closing_balance) AS current_funds, 
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
                    {} 
                  GROUP BY c.id, p.id
                ) AS s 
              ORDER BY new_funds DESC
            ) AS s
        '''.format(where_clause)
        
        cursor = connection.cursor()
        cursor.execute(query, [int(interval)])

        columns = [c[0] for c in cursor.description]
        result_tuple = namedtuple('TopEarners', columns)
        
        return [result_tuple(*r) for r in cursor]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['interval'] = int(self.request.GET.get('interval', 30))

        return context

@method_decorator(xframe_options_exempt, name='dispatch')
class TopEarnersWidgetView(TemplateView):
    template_name = 'camp_fin/widgets/top-earners.html'

    def get_context_data(self, **kwargs):

      with connection.cursor() as cursor:
        cursor.execute(''' 
          SELECT * FROM (
            SELECT 
              dense_rank() OVER (ORDER BY new_funds DESC) AS rank, * 
            FROM (
              SELECT 
                MAX(COALESCE(c.slug, p.slug)) AS slug, 
                MAX(COALESCE(c.full_name, p.name)) AS name, 
                SUM(t.amount) AS new_funds, 
                MAX(f.closing_balance) AS current_funds, 
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
            ORDER BY new_funds DESC
            LIMIT 10
          ) AS s
        ''')

        columns = [c[0] for c in cursor.description]
        transaction_tuple = namedtuple('Transaction', columns)
        top_earners_objects = [transaction_tuple(*r) for r in cursor]

        context = super().get_context_data(**kwargs)
        context['top_earners_objects'] = top_earners_objects
        return context

class Echo(object):
    def write(self, value):
        return value

def iterate_cursor(header, cursor):
    yield header
    
    for row in cursor:
        yield row

def make_response(query, filename):

    cursor = connection.cursor()
    cursor.execute(query)
    header = [c[0] for c in cursor.description]
    
    streaming_buffer = Echo()
    writer = csv.writer(streaming_buffer)
    writer.writerow(header)

    response = StreamingHttpResponse((writer.writerow(row) for row in iterate_cursor(header, cursor)),
                                     content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename={}'.format(filename)

    return response

def bulk_contributions(request):
   
    copy = ''' 
        SELECT
          transaction.*, 
          entity.*
        FROM camp_fin_transaction AS transaction
        JOIN camp_fin_transactiontype AS tt
          ON transaction.transaction_type_id = tt.id
        JOIN camp_fin_filing AS f
          ON transaction.filing_id = f.id
        JOIN camp_fin_filingperiod AS fp
          ON f.filing_period_id = fp.id
        JOIN (
          SELECT 
            entity_id, 
            id, 
            recipient, 
            type 
          FROM (
            SELECT 
              entity_id, 
              id, 
              full_name AS recipient, 
              'candidate' AS type 
            FROM camp_fin_candidate 
            UNION 
            SELECT 
              entity_id, 
              id, 
              name AS recipient, 
              'pac' AS type 
            FROM camp_fin_pac
          ) AS all_entities
        ) AS entity
          ON f.entity_id = entity.entity_id
        WHERE tt.contribution = TRUE
          AND fp.filing_date >= '2010-01-01'
    '''

    filename = 'Contributions_{}.csv'.format(timezone.now().isoformat())
    
    return make_response(copy, filename)

def bulk_expenditures(request):
   
    copy = ''' 
        SELECT
          transaction.*, 
          entity.*
        FROM camp_fin_transaction AS transaction
        JOIN camp_fin_transactiontype AS tt
          ON transaction.transaction_type_id = tt.id
        JOIN camp_fin_filing AS f
          ON transaction.filing_id = f.id
        JOIN camp_fin_filingperiod AS fp
          ON f.filing_period_id = fp.id
        JOIN (
          SELECT 
            entity_id, 
            id, 
            spender, 
            type 
          FROM (
            SELECT 
              entity_id, 
              id, 
              full_name AS spender, 
              'candidate' AS type 
            FROM camp_fin_candidate 
            UNION 
            SELECT 
              entity_id, 
              id, 
              name AS spender, 
              'pac' AS type 
            FROM camp_fin_pac
          ) AS all_entities
        ) AS entity
          ON f.entity_id = entity.entity_id
        WHERE tt.contribution = FALSE
          AND fp.filing_date >= '2010-01-01'
    '''

    filename = 'Expenditures_{}.csv'.format(timezone.now().isoformat())
    
    return make_response(copy, filename)

def bulk_candidates(request):
    
    copy = ''' 
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
        WHERE campaign.date_added >= '2010-01-01'
        ORDER BY candidate.id, election.year DESC
    '''

    filename = 'Candidates_{}.csv'.format(timezone.now().isoformat())
    
    return make_response(copy, filename)

def bulk_committees(request):
    copy = ''' 
        SELECT DISTINCT ON (pac.id)
          pac.*, 
          treasurer.full_name AS treasurer_name 
        FROM camp_fin_pac AS pac
        JOIN camp_fin_treasurer AS treasurer
          ON pac.treasurer_id = treasurer.id
        JOIN camp_fin_filing AS filing
          ON filing.entity_id = pac.entity_id
        WHERE filing.date_added >= '2010-01-01'
        ORDER BY pac.id
    '''

    filename = 'PACs_{}.csv'.format(timezone.now().isoformat())
    
    return make_response(copy, filename)
