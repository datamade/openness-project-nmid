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
from django.db.models import Max, prefetch_related_objects
from django.utils import timezone
from django.core.urlresolvers import reverse_lazy
from django.utils.text import slugify
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.shortcuts import render
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist

from dateutil.rrule import rrule, MONTHLY

from rest_framework import serializers, viewsets, filters, generics, metadata, renderers
from rest_framework.response import Response

from pages.models import Page

from .models import (
    Candidate,
    Office,
    Transaction,
    Campaign,
    Filing,
    PAC,
    LoanTransaction,
    Race,
    RaceGroup,
    OfficeType,
    Entity,
    Lobbyist,
    LobbyistTransaction,
    Organization,
)
from .base_views import (
    PaginatedList,
    TransactionDetail,
    TransactionBaseViewSet,
    TopMoneyView,
    TopEarnersBase,
    PagesMixin,
    TransactionDownloadViewSet,
    Echo,
    iterate_cursor,
    LobbyistTransactionDownloadViewSet,
)
from .api_parts import (
    CandidateSerializer,
    PACSerializer,
    TransactionSerializer,
    TransactionSearchSerializer,
    CandidateSearchSerializer,
    PACSearchSerializer,
    LoanTransactionSerializer,
    TreasurerSearchSerializer,
    DataTablesPagination,
    TransactionCSVRenderer,
    SearchCSVRenderer,
    LobbyistSearchSerializer,
    OrganizationSearchSerializer,
    LobbyistTransactionSearchSerializer,
)
from .templatetags.helpers import format_money, get_transaction_verb

TWENTY_TEN = timezone.make_aware(datetime(2010, 1, 1))


class AboutView(PagesMixin):
    template_name = "about.html"
    page_path = "/about/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "About"
        seo["site_desc"] = "Welcome to New Mexico In Depth’s Openness Project"

        context["seo"] = seo

        return context


class DownloadView(PagesMixin):
    template_name = "downloads.html"
    page_path = "/downloads/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Download defaults
        context["start_date"] = datetime.strptime("2010-01-01", "%Y-%m-%d").date()
        context["end_date"] = datetime.today().date()

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "Data downloads"
        seo[
            "site_desc"
        ] = "Download campaign finance data from New Mexico In Depth’s Openness Project"

        context["seo"] = seo

        return context


class LobbyistContextMixin(object):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["lobbyists"] = Lobbyist.top(limit=5)
        context["organizations"] = Organization.top(limit=5)

        context["num_lobbyists"] = Lobbyist.objects.count()
        context["num_employers"] = Organization.objects.count()

        get_total_contributions = """
            SELECT SUM(political_contributions)
            FROM camp_fin_lobbyistreport
        """

        get_total_expenditures = """
            SELECT SUM(expenditures)
            FROM camp_fin_lobbyistreport
        """

        with connection.cursor() as cursor:
            cursor.execute(get_total_contributions)
            context["total_lobbyist_contributions"] = cursor.fetchone()[0]

            cursor.execute(get_total_expenditures)
            context["total_lobbyist_expenditures"] = cursor.fetchone()[0]

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "Lobbyist portal - The Openness Project"
        seo[
            "site_desc"
        ] = "Browse lobbyists and their employers in New Mexico politics."

        context["seo"] = seo

        return context


class IndexView(TopEarnersBase, LobbyistContextMixin, PagesMixin):
    template_name = "index.html"
    page_path = "/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        year = settings.ELECTION_YEAR
        last_year = str(int(settings.ELECTION_YEAR) - 1)

        context["year"], context["last_year"] = year, last_year

        with connection.cursor() as cursor:
            # Largest donations
            cursor.execute(
                """
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
                WHERE tt.contribution = TRUE
                  AND o.received_date >= '{year}-01-01'
                  AND company_name NOT ILIKE '%public election fund%'
                  AND company_name NOT ILIKE '%department of finance%'
                ORDER BY o.amount DESC
                LIMIT 10
            """.format(
                    year=last_year
                )
            )

            columns = [c[0] for c in cursor.description]
            transaction_tuple = namedtuple("Transaction", columns)
            transaction_objects = [transaction_tuple(*r) for r in cursor]

            # Committees
            cursor.execute(
                """
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
                    WHERE filing.date_added >= '{year}-01-01'
                      AND filing.closing_balance IS NOT NULL
                    ORDER BY pac.id, filing.date_added desc
                  ) AS pac
                ) AS s
                ORDER BY closing_balance DESC
                LIMIT 10
            """.format(
                    year=last_year
                )
            )

            columns = [c[0] for c in cursor.description]
            pac_tuple = namedtuple("PAC", columns)
            pac_objects = [pac_tuple(*r) for r in cursor]

            # Top candidates
            cursor.execute(
                """
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
                    LEFT JOIN camp_fin_office AS office
                      ON campaign.office_id = office.id
                    WHERE filing.date_added >= '{year}-01-01'
                      AND filing.closing_balance IS NOT NULL
                    ORDER BY candidate.id, filing.date_added DESC
                  ) AS candidates
                ) AS s
                LIMIT 10
            """.format(
                    year=last_year
                )
            )

            columns = [c[0] for c in cursor.description]
            candidate_tuple = namedtuple("Candidate", columns)
            candidate_objects = [candidate_tuple(*r) for r in cursor]

        context["transaction_objects"] = transaction_objects
        context["pac_objects"] = pac_objects
        context["candidate_objects"] = candidate_objects

        return context


class LobbyistPortal(LobbyistContextMixin, PagesMixin):
    template_name = "lobbyist-portal.html"
    page_path = "/lobbyist-portal/"


class RacesView(PaginatedList):
    template_name = "camp_fin/races.html"
    page_path = "/races/"

    def get_queryset(self, **kwargs):
        self.year = self.request.GET.get("year", settings.ELECTION_YEAR)

        if len(self.year) != 4:
            # Bogus request
            self.year = settings.ELECTION_YEAR

        self.last_year = str(int(self.year) - 1)

        self.order_by = self.request.GET.get("order_by", "total_funds")
        self.sort_order = self.request.GET.get("sort_order", "desc")
        self.visible = self.request.GET.get("visible")
        self.type = self.request.GET.get("type", 1)

        try:
            self.type = int(self.type)
        except TypeError:
            self.type = 1

        # For now, use office types as groupings for races
        self.race_types = OfficeType.objects.filter(
            race__election_season__year=self.year
        ).distinct()

        if self.visible:
            self.visible = int(self.visible)

        self.type = int(self.type)

        if self.sort_order == "asc":
            ordering = ""
            reverse = False
        else:
            ordering = "-"
            reverse = True

        queryset = Race.objects.filter(election_season__year=self.year)

        if self.type and self.type != "None":
            queryset = queryset.filter(office_type__id=self.type)

        # Prefetch campaign sets to avoid proliferating queries
        queryset = (
            queryset.prefetch_related("campaign_set")
            .prefetch_related("campaign_set__race")
            .prefetch_related("campaign_set__political_party")
            .prefetch_related("campaign_set__candidate")
            .prefetch_related("campaign_set__candidate__entity")
        )

        # Distinguish between columns that can be ordered in SQL, and columns
        # that need to be ordered in Python
        db_order = ("office", "county__name", "district__name", "division__name")
        py_order = ("num_candidates", "total_funds")

        if self.order_by in db_order:
            # For columns that correspond directly to DB attributes, sort the
            # Queryset in SQL
            ordering += self.order_by

            queryset = queryset.order_by(ordering)

        elif self.order_by in py_order:
            # For columns that correspond to properties on the Race model,
            # sort the Queryset in Python (worse performance)
            queryset = sorted(
                queryset, key=lambda race: getattr(race, self.order_by), reverse=reverse
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["sort_order"] = self.sort_order
        context["toggle_order"] = "desc"
        context["year"] = self.year
        context["last_year"] = self.last_year
        context["order_by"] = self.order_by
        context["visible"] = self.visible
        context["type"] = self.type
        context["race_types"] = self.race_types

        try:
            verbose_type = OfficeType.objects.get(id=self.type)
        except OfficeType.DoesNotExist:
            verbose_type = OfficeType.objects.first()

        context["verbose_type"] = verbose_type.description

        if self.sort_order.lower() == "desc":
            context["toggle_order"] = "asc"

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "Contested {year} races in New Mexico".format(year=self.year)
        seo["site_desc"] = "View contested {year} races in New Mexico".format(
            year=self.year
        )

        context["seo"] = seo

        try:
            page = Page.objects.get(path=self.page_path)
            context["page"] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            context["page"] = None

        return context


class RaceDetail(DetailView):
    template_name = "camp_fin/race-detail.html"
    model = Race

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        self.page_path = self.request.path

        race = self.object
        year = race.funding_period

        # Create a map of entity IDs and funding trends for each candidate
        active_entities = [
            Entity.objects.get(id=camp.candidate.entity_id)
            for camp in race.active_campaigns
        ]
        context["active_trends"] = [
            entity.trends(since=year) for entity in active_entities
        ]

        dropout_entities = [
            Entity.objects.get(id=camp.candidate.entity_id)
            for camp in race.sorted_dropouts
        ]
        context["dropout_trends"] = [
            entity.trends(since=year) for entity in dropout_entities
        ]

        # Find max and min of contrib/expend
        context["max"], context["min"] = 0, 0
        for cand in context["active_trends"] + context["dropout_trends"]:
            if cand["donation_trend"]:
                top_donation = max(donation[0] for donation in cand["donation_trend"])

                if top_donation > context["max"]:
                    context["max"] = top_donation

            if cand["expend_trend"]:
                top_expense = min(expense[0] for expense in cand["expend_trend"])

                if top_expense < context["min"]:
                    context["min"] = top_expense

        # Scale charts for labels
        context["max"], context["min"] = context["max"] * 1.1, context["min"] * 1.1

        context["stories"] = race.story_set.all()

        seo = {}
        seo.update(settings.SITE_META)

        race_str = str(race)
        seo["title"] = race_str
        seo[
            "site_desc"
        ] = "View campaign finance contributions for the {race} in New Mexico".format(
            race=race_str
        )

        context["seo"] = seo

        try:
            page = Page.objects.get(path=self.page_path)
            context["page"] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            context["page"] = None

        return context


class DonationsView(PaginatedList):
    template_name = "camp_fin/donations.html"

    def get_queryset(self, **kwargs):
        with connection.cursor() as cursor:
            max_date_query = """
                SELECT
                  MAX(t.received_date)::date
                FROM camp_fin_transaction AS t
                JOIN camp_fin_transactiontype AS tt
                  ON t.transaction_type_id = tt.id
                WHERE tt.contribution = TRUE
                  AND t.received_date <= NOW()
            """
            cursor.execute(max_date_query)
            max_date = cursor.fetchone()[0]

            self.order_by = self.request.GET.get("order_by", "received_date")
            self.sort_order = self.request.GET.get("sort_order", "asc")

            query = """
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
                  AND o.received_date::date BETWEEN %s AND %s
                  AND company_name NOT ILIKE '%%public election fund%%'
                  AND company_name NOT ILIKE '%%department of finance%%'
                ORDER BY {0} {1}
            """.format(
                self.order_by, self.sort_order
            )

            start_date_str = self.request.GET.get("from")
            end_date_str = self.request.GET.get("to")

            if start_date_str and end_date_str:
                self.start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                self.end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            elif start_date_str and not end_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                self.start_date = start_date
                self.end_date = start_date + timedelta(days=1)

            elif not start_date_str and end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                self.start_date = end_date - timedelta(days=1)
                self.end_date = end_date

            else:
                self.end_date = max_date
                self.start_date = max_date

            cursor.execute(query, [self.start_date, self.end_date])

            columns = [c[0] for c in cursor.description]
            result_tuple = namedtuple("Transaction", columns)
            donation_objects = [result_tuple(*r) for r in cursor]

            self.donation_count = len(donation_objects)
            self.donation_sum = sum([d.amount for d in donation_objects])

            return donation_objects

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["sort_order"] = self.sort_order
        context["toggle_order"] = "desc"

        if self.sort_order.lower() == "desc":
            context["toggle_order"] = "asc"

        context["order_by"] = self.order_by

        context["start_date"] = self.start_date
        context["end_date"] = self.end_date
        context["donation_count"] = self.donation_count
        context["donation_sum"] = self.donation_sum

        seo = {}
        seo.update(settings.SITE_META)

        start_date = self.start_date.strftime("%B %-d, %Y")
        end_date = self.end_date.strftime("%B %-d, %Y")
        count = "{:,}".format(self.donation_count)
        total = format_money(self.donation_sum)

        fmt_args = {
            "start_date": start_date,
            "count": count,
            "total": total,
            "end_date": end_date,
        }

        if start_date != end_date:
            seo["title"] = "Donations between {start_date} and {end_date}".format(
                **fmt_args
            )
            seo[
                "site_desc"
            ] = "{count} donations between {start_date} and {end_date} totalling {total}".format(
                **fmt_args
            )

        else:
            seo["title"] = "Donations on {start_date}".format(**fmt_args)
            seo[
                "site_desc"
            ] = "{count} donations on {start_date} totalling {total}".format(**fmt_args)

        context["seo"] = seo

        return context


class SearchView(TemplateView):
    template_name = "camp_fin/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["term"] = self.request.GET.get("term")
        context["table_name"] = self.request.GET.getlist("table_name")

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "Search for '{}'".format(context["term"])
        seo["site_desc"] = "Search for candidates, committees and donors in New Mexico"

        context["seo"] = seo

        return context


class CandidateList(PaginatedList):
    template_name = "camp_fin/candidate-list.html"
    page_path = "/candidates/"

    def get_queryset(self, **kwargs):
        cursor = connection.cursor()

        self.order_by = self.request.GET.get("order_by", "closing_balance")
        self.sort_order = self.request.GET.get("sort_order", "desc")

        cursor.execute(
            """
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
                  COALESCE(period.filing_date, filing.date_added) AS filing_date
                FROM camp_fin_candidate AS candidate
                JOIN camp_fin_filing AS filing
                  USING(entity_id)
                LEFT JOIN camp_fin_filingperiod AS period
                  ON filing.filing_period_id = period.id
                JOIN camp_fin_campaign AS campaign
                  ON filing.campaign_id = campaign.id
                LEFT JOIN camp_fin_office AS office
                  ON campaign.office_id = office.id
                WHERE filing.date_added >= '2010-01-01'
                  AND filing.closing_balance IS NOT NULL
                ORDER BY candidate.id, filing.date_added DESC
              ) AS candidates
            ) AS s
            ORDER BY {0} {1}
        """.format(
                self.order_by, self.sort_order
            )
        )

        columns = [c[0] for c in cursor.description]
        candidate_tuple = namedtuple("Candidate", columns)

        return [candidate_tuple(*r) for r in cursor]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["sort_order"] = self.sort_order

        context["toggle_order"] = "desc"
        if self.sort_order.lower() == "desc":
            context["toggle_order"] = "asc"

        context["order_by"] = self.order_by

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "Candidates"
        seo["site_desc"] = "Candidates in New Mexico"

        context["seo"] = seo

        try:
            page = Page.objects.get(path=self.page_path)
            context["page"] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            context["page"] = None

        return context


class CommitteeList(PaginatedList):
    template_name = "camp_fin/committee-list.html"
    page_path = "/committees/"

    def get_queryset(self, **kwargs):
        cursor = connection.cursor()

        self.order_by = self.request.GET.get("order_by", "closing_balance")
        self.sort_order = self.request.GET.get("sort_order", "desc")

        cursor.execute(
            """
            SELECT * FROM (
              SELECT
                DENSE_RANK() OVER (ORDER BY closing_balance DESC) AS rank,
                pac.*
              FROM (
                SELECT DISTINCT ON (pac.id)
                  pac.*,
                  filing.closing_balance,
                  COALESCE(period.filing_date, filing.date_added) AS filing_date
                FROM camp_fin_pac AS pac
                JOIN camp_fin_filing AS filing
                  USING(entity_id)
                LEFT JOIN camp_fin_filingperiod AS period
                  ON filing.filing_period_id = period.id
                WHERE filing.date_added >= '2010-01-01'
                  AND filing.closing_balance IS NOT NULL
                ORDER BY pac.id, filing.date_added DESC
              ) AS pac
            ) AS s
            ORDER BY {0} {1}
        """.format(
                self.order_by, self.sort_order
            )
        )

        columns = [c[0] for c in cursor.description]
        pac_tuple = namedtuple("PAC", columns)

        return [pac_tuple(*r) for r in cursor]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["sort_order"] = self.sort_order

        context["toggle_order"] = "desc"
        if self.sort_order.lower() == "desc":
            context["toggle_order"] = "asc"

        context["order_by"] = self.order_by

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "PACs"
        seo["site_desc"] = "PACs in New Mexico"

        context["seo"] = seo

        try:
            page = Page.objects.get(path=self.page_path)
            context["page"] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            context["page"] = None

        return context


class LobbyistList(PaginatedList):
    template_name = "camp_fin/lobbyists.html"
    page_path = "/lobbyists/"

    def get_queryset(self, **kwargs):
        self.order_by = self.request.GET.get("order_by", "rank")
        # Handle empty string
        if not self.order_by:
            self.order_by = "rank"

        assert self.order_by in ["rank", "contributions", "expenditures"]

        self.sort_order = self.request.GET.get("sort_order", "asc")
        if not self.sort_order:
            self.sort_order = "asc"

        assert self.sort_order in ["asc", "desc"]

        queryset = Lobbyist.top(order_by=self.order_by, sort_order=self.sort_order)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["sort_order"] = self.sort_order
        context["order_by"] = self.order_by

        if self.sort_order.lower() == "desc":
            context["toggle_order"] = "asc"
        else:
            context["toggle_order"] = "desc"

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "Lobbyists in New Mexico"
        seo["site_desc"] = "Browse active lobbyists in New Mexico"

        context["seo"] = seo

        try:
            page = Page.objects.get(path=self.page_path)
            context["page"] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            context["page"] = None

        return context


class LobbyistDetail(DetailView):
    template_name = "camp_fin/lobbyist-detail.html"
    model = Lobbyist

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        self.page_path = self.request.path

        # Determine how many employers
        last_year_employed = (
            self.object.lobbyistemployer_set.all()
            .aggregate(last_year_employed=Max("year"))
            .get("last_year_employed")
        )

        context["last_year_employed"] = last_year_employed

        if last_year_employed:
            context["num_recent_employers"] = self.object.lobbyistemployer_set.filter(
                year=last_year_employed
            ).count()
        else:
            context["num_recent_employers"] = 0

        # Get variables for sorting and ordering
        contrib_order_by = self.request.GET.get("contrib_order_by", "amount")
        expend_order_by = self.request.GET.get("expend_order_by", "amount")

        # Handle empty string
        if not contrib_order_by:
            contrib_order_by = "amount"
        if not expend_order_by:
            expend_order_by = "amount"

        assert contrib_order_by in ["recipient", "amount", "received_date"]
        assert expend_order_by in [
            "recipient",
            "amount",
            "beneficiary",
            "received_date",
        ]

        contrib_sort_order = self.request.GET.get("contrib_sort_order", "desc")
        expend_sort_order = self.request.GET.get("expend_sort_order", "desc")

        if not contrib_sort_order:
            contrib_sort_order = "asc"
        if not expend_sort_order:
            expend_sort_order = "asc"

        assert contrib_sort_order in ["asc", "desc"]
        assert expend_sort_order in ["asc", "desc"]

        context["contrib_sort_order"] = contrib_sort_order
        context["expend_sort_order"] = expend_sort_order

        if contrib_sort_order == "asc":
            context["contrib_toggle_order"] = "desc"
        else:
            context["contrib_toggle_order"] = "asc"

        if expend_sort_order == "asc":
            context["expend_toggle_order"] = "desc"
        else:
            context["expend_toggle_order"] = "asc"

        context["contrib_order_by"] = contrib_order_by
        context["expend_order_by"] = expend_order_by

        contributions = context["object"].contributions(
            order_by=contrib_order_by, ordering=contrib_sort_order
        )

        expenditures = context["object"].expenditures(
            order_by=expend_order_by, ordering=expend_sort_order
        )

        # Paginate contributions and expenditures
        contrib_paginator = Paginator(contributions, 15)
        contrib_page = self.request.GET.get("contrib_page", 1)

        try:
            context["contributions"] = contrib_paginator.page(contrib_page)
        except PageNotAnInteger:
            context["contributions"] = contrib_paginator.page(1)
        except EmptyPage:
            context["contributions"] = contrib_paginator.page(
                contrib_paginator.num_pages
            )

        expend_paginator = Paginator(expenditures, 15)
        expend_page = self.request.GET.get("expend_page", 1)

        try:
            context["expenditures"] = expend_paginator.page(expend_page)
        except PageNotAnInteger:
            context["expenditures"] = expend_paginator.page(1)
        except EmptyPage:
            context["expenditures"] = expend_paginator.page(expend_paginator.num_pages)

        sos_link = "https://www.cfis.state.nm.us/media/ReportLobbyist.aspx?id={id}&el=0"
        context["sos_link"] = sos_link.format(id=context["object"].id)

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "Lobbyist in New Mexico"
        seo["site_desc"] = "View details of a lobbyist in New Mexico"

        context["seo"] = seo

        try:
            page = Page.objects.get(path=self.page_path)
            context["page"] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            context["page"] = None

        return context


class OrganizationList(PaginatedList):
    template_name = "camp_fin/organizations.html"
    page_path = "/organizations/"

    def get_queryset(self, **kwargs):
        self.order_by = self.request.GET.get("order_by", "rank")

        # Handle empty string
        if not self.order_by:
            self.order_by = "rank"

        assert self.order_by in ["rank", "contributions", "expenditures"]

        self.sort_order = self.request.GET.get("sort_order", "asc")
        if not self.sort_order:
            self.sort_order = "asc"

        assert self.sort_order in ["asc", "desc"]

        queryset = Organization.top(order_by=self.order_by, sort_order=self.sort_order)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["sort_order"] = self.sort_order
        context["order_by"] = self.order_by

        if self.sort_order.lower() == "desc":
            context["toggle_order"] = "asc"
        else:
            context["toggle_order"] = "desc"

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "Lobbyist employers in New Mexico"
        seo["site_desc"] = "Browse active lobbyist employers in New Mexico"

        context["seo"] = seo

        try:
            page = Page.objects.get(path=self.page_path)
            context["page"] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            context["page"] = None

        return context


class OrganizationDetail(DetailView):
    template_name = "camp_fin/organization-detail.html"
    model = Organization

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        self.page_path = self.request.path

        # Get variables for sorting and ordering
        contrib_order_by = self.request.GET.get("contrib_order_by", "amount")
        expend_order_by = self.request.GET.get("expend_order_by", "amount")

        # Handle empty string
        if not contrib_order_by:
            contrib_order_by = "amount"
        if not expend_order_by:
            expend_order_by = "amount"

        assert contrib_order_by in ["recipient", "amount", "received_date"]
        assert expend_order_by in [
            "recipient",
            "amount",
            "beneficiary",
            "received_date",
        ]

        contrib_sort_order = self.request.GET.get("contrib_sort_order", "desc")
        expend_sort_order = self.request.GET.get("expend_sort_order", "desc")

        if not contrib_sort_order:
            contrib_sort_order = "asc"
        if not expend_sort_order:
            expend_sort_order = "asc"

        assert contrib_sort_order in ["asc", "desc"]
        assert expend_sort_order in ["asc", "desc"]

        context["contrib_sort_order"] = contrib_sort_order
        context["expend_sort_order"] = expend_sort_order

        if contrib_sort_order == "asc":
            context["contrib_toggle_order"] = "desc"
        else:
            context["contrib_toggle_order"] = "asc"

        if expend_sort_order == "asc":
            context["expend_toggle_order"] = "desc"
        else:
            context["expend_toggle_order"] = "asc"

        context["contrib_order_by"] = contrib_order_by
        context["expend_order_by"] = expend_order_by

        contributions = context["object"].contributions(
            order_by=contrib_order_by, ordering=contrib_sort_order
        )

        expenditures = context["object"].expenditures(
            order_by=expend_order_by, ordering=expend_sort_order
        )

        # Paginate contributions and expenditures
        contrib_paginator = Paginator(contributions, 15)
        contrib_page = self.request.GET.get("contrib_page", 1)

        try:
            context["contributions"] = contrib_paginator.page(contrib_page)
        except PageNotAnInteger:
            context["contributions"] = contrib_paginator.page(1)
        except EmptyPage:
            context["contributions"] = contrib_paginator.page(
                contrib_paginator.num_pages
            )

        expend_paginator = Paginator(expenditures, 15)
        expend_page = self.request.GET.get("expend_page", 1)

        try:
            context["expenditures"] = expend_paginator.page(expend_page)
        except PageNotAnInteger:
            context["expenditures"] = expend_paginator.page(1)
        except EmptyPage:
            context["expenditures"] = expend_paginator.page(expend_paginator.num_pages)

        sos_link = "https://www.cfis.state.nm.us/media/ReportEmployer.aspx?id={id}&el=0"
        context["sos_link"] = sos_link.format(id=context["object"].id)

        seo = {}
        seo.update(settings.SITE_META)

        name = context["object"].name

        seo["title"] = "Lobbyist employer {name} in New Mexico".format(name=name)
        seo["site_desc"] = (
            "View expenditures and contributions from "
            + "{name}, a lobbyist employer in New Mexico".format(name=name)
        )

        context["seo"] = seo

        try:
            page = Page.objects.get(path=self.page_path)
            context["page"] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            context["page"] = None

        return context


class LobbyistTransactionList(PaginatedList):
    template_name = "camp_fin/lobbyist-transaction-list.html"
    page_path = "/transactions/"

    def get_queryset(self, **kwargs):
        queryset = LobbyistTransaction.objects.all()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "Lobbyist transactions in New Mexico"
        seo[
            "site_desc"
        ] = "Browse contributions and expenditures of lobbyists in New Mexico"

        context["seo"] = seo

        try:
            page = Page.objects.get(path=self.page_path)
            context["page"] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            context["page"] = None

        return context


class CommitteeDetailBaseView(DetailView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        entity_id = context["object"].entity_id
        entity = Entity.objects.get(id=entity_id)

        # Determine the date of the first contribution/expenditure
        min_date_query = """
            WITH all_cash AS (
                SELECT month
                FROM contributions_by_month
                WHERE entity_id = %s
                UNION
                SELECT month
                FROM expenditures_by_month
                WHERE entity_id = %s
              )
            SELECT COALESCE(MIN(all_cash.month::date), '2010-01-01'::date)
            FROM all_cash
        """

        with connection.cursor() as cursor:
            cursor.execute(min_date_query, [entity.id, entity.id])
            row = cursor.fetchone()

        if row[0].year > 2010:
            year = str(row[0].year)
        else:
            year = "2010"

        trends = entity.trends(since=year)
        context.update(trends)

        latest_filing = (
            context["object"]
            .entity.filing_set.filter(filing_period__exclude_from_cascading=False)
            .exclude(final__isnull=True)
            .order_by("-date_added")
            .first()
        )

        context["latest_filing"] = latest_filing

        if latest_filing:
            total_loans = latest_filing.total_loans or 0
            total_inkind = latest_filing.total_inkind or 0

            # Count pure donations, if applicable
            if total_loans > 0 or total_inkind > 0:
                donations = latest_filing.total_contributions - (
                    latest_filing.total_loans + latest_filing.total_inkind
                )
                context["donations"] = donations

        print(context)
        print(entity_id)

        return context


class CandidateDetail(CommitteeDetailBaseView):
    template_name = "camp_fin/candidate-detail.html"
    model = Candidate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_loans = """
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
        """

        cursor = connection.cursor()

        cursor.execute(current_loans, [context["object"].id])

        columns = [c[0] for c in cursor.description]
        loan_tuple = namedtuple("Loans", columns)

        context["loans"] = [loan_tuple(*r) for r in cursor]

        latest_campaign = (
            context["object"].campaign_set.order_by("-election_season__year").first()
        )

        context["latest_campaign"] = latest_campaign

        context["campaigns"] = context["object"].campaign_set.all()

        context["stories"] = self.object.story_set.all()

        seo = {}
        seo.update(settings.SITE_META)

        first_name = context["object"].first_name
        last_name = context["object"].last_name

        seo["title"] = "{0} {1}".format(first_name, last_name)
        seo["site_desc"] = "Candidate information for {0} {1}".format(
            first_name, last_name
        )

        context["seo"] = seo

        try:
            latest_campaign = context["latest_filing"].campaign
        except (AttributeError, ObjectDoesNotExist):
            latest_campaign = None

        sos_link = None

        if latest_campaign and latest_campaign in Campaign.objects.exclude(
            office__id=0
        ):
            try:
                sos_link = "https://www.cfis.state.nm.us/media/CandidateReportH.aspx?es={es}&ot={ot}&o={o}&c={c}"
                sos_link = sos_link.format(
                    es=latest_campaign.election_season.id,
                    ot=latest_campaign.office.office_type.id,
                    o=latest_campaign.office.id,
                    c=latest_campaign.candidate_id,
                )
            except AttributeError:
                sos_link = None

        context["sos_link"] = sos_link
        context["entity_type"] = "candidate"

        return context


class CommitteeDetail(CommitteeDetailBaseView):
    template_name = "camp_fin/committee-detail.html"
    model = PAC

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "{0}".format(context["object"].name)
        seo["site_desc"] = "Information about '{0}' in New Mexico".format(
            context["object"].name
        )

        context["seo"] = seo

        context[
            "sos_link"
        ] = "https://www.cfis.state.nm.us/media/PACReport.aspx?p={}".format(
            context["object"].entity_id
        )

        context["entity_type"] = "pac"

        return context


class ContributionDetail(TransactionDetail):
    template_name = "camp_fin/contribution-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        seo = {}
        seo.update(settings.SITE_META)

        transaction_verb = get_transaction_verb(
            context["object"].transaction_type.description
        )
        contributor = context["object"].full_name
        amount = format_money(context["object"].amount)

        if hasattr(context["entity"], "name"):
            recipient = context["entity"].name
        else:
            recipient = "{0} {1}".format(
                context["entity"].first_name, context["entity"].last_name
            )

        seo["title"] = "{0} {1} to {2}".format(contributor, transaction_verb, recipient)

        seo["site_desc"] = "{0} {1} {2} to {3}".format(
            contributor, transaction_verb, amount, recipient
        )

        context["seo"] = seo

        return context


class ExpenditureDetail(TransactionDetail):
    template_name = "camp_fin/expenditure-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        seo = {}
        seo.update(settings.SITE_META)

        transaction_verb = get_transaction_verb(
            context["object"].transaction_type.description
        )
        vendor = context["object"].full_name
        amount = format_money(context["object"].amount)

        if hasattr(context["entity"], "name"):
            pac = context["entity"].name
        else:
            pac = "{0} {1}".format(
                context["entity"].first_name, context["entity"].last_name
            )

        seo["title"] = "Expenditure by {0}".format(pac)

        seo["site_desc"] = "{0} {1} {2} on {3}".format(
            pac, transaction_verb, amount, vendor
        )

        context["seo"] = seo

        return context


class TransactionViewSet(TransactionBaseViewSet):
    serializer_class = TransactionSerializer
    renderer_classes = (renderers.JSONRenderer, TransactionCSVRenderer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if request.GET.get("format") == "csv":
            if self.default_filter["transaction_type__contribution"]:
                ttype = "contributions"
            else:
                ttype = "expenditures"

            if not self.entity_name:
                response = HttpResponse(
                    "Use /api/bulk/{}/ to get bulk downloads".format(ttype)
                )
                response.status_code = 400

            else:
                filename = "{0}-{1}-{2}.csv".format(
                    ttype, slugify(self.entity_name), timezone.now().isoformat()
                )

                response["Content-Disposition"] = "attachment; filename={}".format(
                    filename
                )

        return response


class ContributionViewSet(TransactionViewSet):
    """
    ViewSet for the contribution API, returning JSON.
    """

    default_filter = {
        "transaction_type__contribution": True,
        "filing__date_added__gte": TWENTY_TEN,
    }


class ExpenditureViewSet(TransactionViewSet):
    """
    Viewset for the expenditure API, returning JSON.
    """

    default_filter = {
        "transaction_type__contribution": False,
        "filing__date_added__gte": TWENTY_TEN,
    }


class ContributionDownloadViewSet(TransactionDownloadViewSet):
    """
    Viewset for the contribution API, returning bulk downloads as CSV.
    """

    contribution = True


class ExpenditureDownloadViewSet(TransactionDownloadViewSet):
    """
    Viewset for the expenditures API, returning bulk downloads as CSV.
    """

    contribution = False


class LobbyistContributionViewSet(LobbyistTransactionDownloadViewSet):
    """
    Viewset for Lobbyist contribution API, returning bulk downloads as CSV.
    """

    contribution = True


class LobbyistExpenditureViewSet(LobbyistTransactionDownloadViewSet):
    """
    Viewset for Lobbyist expenditure API, returning bulk downloads as CSV.
    """

    contribution = False


class TopDonorsView(TopMoneyView):
    contribution = True


class TopExpensesView(TopMoneyView):
    contribution = False


class LoanViewSet(TransactionBaseViewSet):
    queryset = LoanTransaction.objects.filter(transaction_date__gte=TWENTY_TEN)
    serializer_class = LoanTransactionSerializer


SERIALIZER_LOOKUP = {
    "candidate": CandidateSearchSerializer,
    "pac": PACSearchSerializer,
    "contribution": TransactionSearchSerializer,
    "expenditure": TransactionSearchSerializer,
    "lobbyist": LobbyistSearchSerializer,
    "organization": OrganizationSearchSerializer,
    "lobbyisttransaction": LobbyistTransactionSearchSerializer,
}


@method_decorator(never_cache, name="dispatch")
class SearchAPIView(viewsets.ViewSet):
    renderer_classes = (renderers.JSONRenderer, SearchCSVRenderer)

    def list(self, request):
        table_names = request.GET.getlist("table_name")
        term = request.GET.get("term")
        datatype = request.GET.get("datatype")

        print(term)

        limit = request.GET.get("limit", 50)
        offset = request.GET.get("offset", 0)

        order_by_col = None
        sort_order = "ASC"

        if request.GET.get("length"):
            limit = request.GET["length"]

        if request.GET.get("start"):
            offset = request.GET["start"]

        if request.GET.get("order[0][column]"):
            col_idx = request.GET["order[0][column]"]
            order_by_col = request.GET["columns[" + str(col_idx) + "][data]"]

            sort_order = request.GET["order[0][dir]"]

        if not term:
            return Response({"error": "term is required"}, status=400)

        if not table_names:
            table_names = [
                "candidate",
                "pac",
                "contribution",
                "expenditure",
                "lobbyist",
                "organization",
                "lobbyisttransaction",
            ]

        response = {}

        for table in table_names:
            if table == "pac":
                query = """
                    SELECT * FROM (
                      SELECT DISTINCT ON (pac.id)
                        pac.*,
                        address.street || ' ' ||
                        address.city || ', ' ||
                        state.postal_code || ' ' ||
                        address.zipcode AS address
                     FROM camp_fin_pac AS pac
                     LEFT JOIN camp_fin_address AS address
                        ON pac.address_id = address.id
                     LEFT JOIN camp_fin_state AS state
                        ON address.state_id = state.id
                     JOIN camp_fin_filing AS filing
                        ON filing.entity_id = pac.entity_id
                     WHERE pac.search_name @@ plainto_tsquery('english', %s)
                        AND filing.date_added >= '2010-01-01'
                     ORDER BY pac.id
                    ) AS s
                """.format(
                    table
                )

            if table == "candidate":
                query = """
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
                      LEFT JOIN camp_fin_politicalparty AS party
                        ON campaign.political_party_id = party.id
                      LEFT JOIN camp_fin_county AS county
                        ON campaign.county_id = county.id
                      LEFT JOIN camp_fin_office AS office
                        ON campaign.office_id = office.id
                      LEFT JOIN camp_fin_officetype AS officetype
                        ON office.office_type_id = officetype.id
                      LEFT JOIN camp_fin_district AS district
                        ON campaign.district_id = district.id
                      LEFT JOIN camp_fin_division AS division
                        ON campaign.division_id = division.id
                      WHERE candidate.search_name @@ plainto_tsquery('english', %s)
                        AND campaign.date_added >= '2010-01-01'
                      ORDER BY candidate.id, election.year DESC
                    ) AS s
                """.format(
                    table
                )

            if table == "contribution":
                query = """
                    SELECT
                      o.*,
                      CASE WHEN o.occupation = 'None' THEN ''
                           ELSE initcap(o.occupation)
                      END AS donor_occupation,
                      tt.description AS transaction_type,
                      CASE WHEN
                        pac.name IS NULL OR TRIM(pac.name) = ''
                      THEN
                        candidate.full_name
                      ELSE pac.name
                      END AS transaction_subject,
                      pac.slug AS pac_slug,
                      candidate.slug AS candidate_slug,
                      o.address || ' ' ||
                        o.city || ', ' ||
                        o.state || ' ' ||
                        o.zipcode AS full_address
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
                    LEFT JOIN camp_fin_contact AS contact
                      ON o.contact_id = contact.id
                    LEFT JOIN camp_fin_address AS address
                      ON contact.address_id = address.id
                    LEFT JOIN camp_fin_state AS state
                      ON address.state_id = state.id
                    WHERE o.search_name @@ plainto_tsquery('english', %s)
                      AND tt.contribution = TRUE
                      AND o.received_date >= '2010-01-01'
                """

            elif table == "expenditure":
                query = """
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
                """

            elif table == "lobbyist":
                query = """
                    SELECT
                        lob.slug,
                        concat_ws(' ', lob.prefix, lob.first_name, lob.middle_name,
                                       lob.last_name, lob.suffix)
                        AS name
                    FROM camp_fin_lobbyist AS lob
                    WHERE lob.search_name @@ plainto_tsquery('english', %s)
                """

            elif table == "organization":
                query = """
                    SELECT
                        org.name AS name,
                        org.slug AS slug,
                        CASE WHEN
                            add.street IS NULL OR TRIM(add.street) = ''
                        THEN
                            ''
                        ELSE
                            add.street || ' ' ||
                            add.city || ', ' ||
                            state.postal_code || ' ' ||
                            add.zipcode
                        END AS address
                    FROM camp_fin_organization AS org
                    JOIN camp_fin_address AS add
                      ON org.permanent_address_id = add.id
                    JOIN camp_fin_state AS state
                      ON add.state_id = state.id
                    WHERE org.search_name @@ plainto_tsquery('english', %s)
                """

            elif table == "lobbyisttransaction":
                query = """
                    SELECT
                      lobbyist.slug AS lobbyist_slug,
                      concat_ws(' ', lobbyist.prefix, lobbyist.first_name, lobbyist.middle_name,
                                     lobbyist.last_name, lobbyist.suffix) AS lobbyist_name,
                      trans.name,
                      trans.beneficiary,
                      trans.expenditure_purpose,
                      trans.received_date,
                      trans.amount,
                      trans.date_added,
                      tt.description AS transaction_type,
                      CASE WHEN tt.group_id = 2
                        THEN 'Political contribution'
                      ELSE 'Candidate'
                      END AS transaction_group
                    FROM camp_fin_lobbyisttransaction AS trans
                    JOIN camp_fin_lobbyisttransactiontype AS tt
                      ON trans.lobbyist_transaction_type_id = tt.id
                    JOIN camp_fin_lobbyistreport AS report
                      ON trans.lobbyist_report_id = report.id
                    JOIN camp_fin_lobbyist AS lobbyist
                      ON report.entity_id = lobbyist.entity_id
                    WHERE trans.search_name @@ plainto_tsquery('english', %s)
                """

            if order_by_col:
                query = """
                    {0} ORDER BY {1} {2}
                """.format(
                    query, order_by_col, sort_order
                )

            serializer = SERIALIZER_LOOKUP[table]

            cursor = connection.cursor()
            cursor.execute(query, [term])

            columns = [c[0] for c in cursor.description]
            result_tuple = namedtuple(table, columns)

            objects = [result_tuple(*r) for r in cursor]

            meta = OrderedDict()

            if not request.GET.get("format") == "csv":
                paginator = DataTablesPagination()

                page = paginator.paginate_queryset(objects, self.request, view=self)

                serializer = serializer(page, many=True)

                objects = serializer.data

                draw = int(request.GET.get("draw", 0))

                meta = OrderedDict(
                    [
                        ("total_rows", paginator.count),
                        ("limit", limit),
                        ("offset", offset),
                        ("recordsTotal", paginator.count),
                        ("recordsFiltered", limit),
                        ("draw", draw),
                    ]
                )

            response[table] = OrderedDict(
                [
                    ("meta", meta),
                    ("objects", objects),
                ]
            )

        return Response(response)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if request.GET.get("format") == "csv":
            term = request.GET["term"]

            filename = "{0}-{1}.zip".format(slugify(term), timezone.now().isoformat())

            response["Content-Disposition"] = "attachment; filename={}".format(filename)

        return response


class TopEarnersView(PaginatedList):
    template_name = "camp_fin/top-earners.html"
    per_page = 100

    def get_queryset(self):
        interval = self.request.GET.get("interval", 90)

        if int(interval) > 0:
            where_clause = "AND t.received_date >= (NOW() - INTERVAL '%s days')"
        else:
            where_clause = "AND t.received_date >= '2010-01-01'"

        query = """
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
                    {}
                  GROUP BY c.id, p.id
                ) AS s
                WHERE name NOT ILIKE '%%public election fund%%'
                  OR name NOT ILIKE '%%department of finance%%'
              ORDER BY new_funds DESC
            ) AS s
        """.format(
            where_clause
        )

        cursor = connection.cursor()
        cursor.execute(query, [int(interval)])

        columns = [c[0] for c in cursor.description]
        result_tuple = namedtuple("TopEarners", columns)

        return [result_tuple(*r) for r in cursor]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["interval"] = int(self.request.GET.get("interval", 90))

        seo = {}
        seo.update(settings.SITE_META)

        seo["title"] = "Top earners"
        seo[
            "site_desc"
        ] = "Top earning political committees and candidates in New Mexico"

        context["seo"] = seo

        return context


@method_decorator(xframe_options_exempt, name="dispatch")
class TopEarnersWidgetView(TopEarnersBase):
    template_name = "camp_fin/widgets/top-earners.html"


def make_response(query, filename, args=[]):
    cursor = connection.cursor()

    if args:
        cursor.execute(query, args)
    else:
        cursor.execute(query)

    header = [c[0] for c in cursor.description]

    streaming_buffer = Echo()
    writer = csv.writer(streaming_buffer)
    writer.writerow(header)

    response = StreamingHttpResponse(
        (writer.writerow(row) for row in iterate_cursor(header, cursor)),
        content_type="text/csv",
    )
    response["Content-Disposition"] = "attachment; filename={}".format(filename)

    return response


def bulk_candidates(request):
    copy = """
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
        LEFT JOIN camp_fin_office AS office
          ON campaign.office_id = office.id
        JOIN camp_fin_officetype AS officetype
          ON office.office_type_id = officetype.id
        LEFT JOIN camp_fin_district AS district
          ON campaign.district_id = district.id
        LEFT JOIN camp_fin_division AS division
          ON campaign.division_id = division.id
        WHERE campaign.date_added >= '2010-01-01'
    """

    args = []

    if request.GET.get("from"):
        start_date = request.GET.get("from")
        args.append(start_date)
        copy += """
            AND campaign.date_added >= %s
        """

    if request.GET.get("to"):
        end_date = request.GET.get("to")
        args.append(end_date)
        copy += """
            AND campaign.date_added <= %s
        """

    copy += """
        ORDER BY candidate.id, election.year DESC
    """

    filename = "Candidates_{}.csv".format(timezone.now().isoformat())

    return make_response(copy, filename, args)


def bulk_committees(request):
    copy = """
        SELECT DISTINCT ON (pac.id)
          pac.*,
          treasurer.full_name AS treasurer_name
        FROM camp_fin_pac AS pac
        JOIN camp_fin_treasurer AS treasurer
          ON pac.treasurer_id = treasurer.id
        JOIN camp_fin_filing AS filing
          ON filing.entity_id = pac.entity_id
        WHERE filing.date_added >= '2010-01-01'
    """

    args = []

    if request.GET.get("from"):
        start_date = request.GET.get("from")
        args.append(start_date)
        copy += """
            AND filing.date_added >= %s
        """

    if request.GET.get("to"):
        end_date = request.GET.get("to")
        args.append(end_date)
        copy += """
            AND filing.date_added <= %s
        """

    copy += """
        ORDER BY pac.id
    """

    filename = "PACs_{}.csv".format(timezone.now().isoformat())

    return make_response(copy, filename, args)


def bulk_lobbyists(request):
    """
    Return a CSV containing all Lobbyists.
    """
    copy = """
        SELECT
            lobbyist.id,
            lobbyist.date_added,
            lobbyist.date_updated,
            lobbyist.prefix,
            lobbyist.first_name,
            lobbyist.middle_name,
            lobbyist.last_name,
            lobbyist.suffix,
            lobbyist.email,
            lobbyist.phone,
            lobbyist.registration_date,
            lobbyist.termination_date,
            lobbyist.entity_id
        FROM camp_fin_lobbyist AS lobbyist
        WHERE lobbyist.registration_date >= '2010-01-01'
    """

    args = []

    if request.GET.get("from"):
        start_date = request.GET.get("from")
        args.append(start_date)
        copy += """
            AND lobbyist.registration_date >= %s
        """

    if request.GET.get("to"):
        end_date = request.GET.get("to")
        args.append(end_date)
        copy += """
            AND lobbyist.registration_date <= %s
        """

    copy += """
        ORDER BY lobbyist.id
    """

    filename = "Lobbyists_{}.csv".format(timezone.now().isoformat())

    return make_response(copy, filename, args)


def bulk_employers(request):
    copy = """
        SELECT
            org.id,
            org.date_added,
            org.date_updated,
            org.name,
            org.email,
            org.phone,
            org.entity_id
        FROM camp_fin_organization AS org
        WHERE org.date_added >= '2010-01-01'
    """

    args = []

    if request.GET.get("from"):
        start_date = request.GET.get("from")
        args.append(start_date)
        copy += """
            AND org.date_added >= %s
        """

    if request.GET.get("to"):
        end_date = request.GET.get("to")
        args.append(end_date)
        copy += """
            AND org.date_added <= %s
        """

    copy += """
        ORDER BY org.id
    """

    filename = "Employers_{}.csv".format(timezone.now().isoformat())

    return make_response(copy, filename, args)


def bulk_employments(request):
    copy = """
        SELECT
            emp.id,
            emp.date_added,
            emp.year,
            emp.organization_id,
            org.name AS organization_name,
            emp.lobbyist_id,
            lobbyist.first_name AS lobbyist_first_name,
            lobbyist.middle_name AS lobbyist_middle_name,
            lobbyist.last_name AS lobbyist_last_name
        FROM camp_fin_lobbyistemployer AS emp
        JOIN camp_fin_lobbyist AS lobbyist
          ON emp.lobbyist_id = lobbyist.id
        JOIN camp_fin_organization AS org
          ON emp.organization_id = org.id
        WHERE year >= '2010'
    """

    args = []

    if request.GET.get("from"):
        start_date = request.GET.get("from")

        # Only get the year
        start_date = start_date[:4]

        args.append(start_date)
        copy += """
            AND year >= %s
        """

    if request.GET.get("to"):
        end_date = request.GET.get("to")

        # Only get the year
        end_date = end_date[:4]

        args.append(end_date)
        copy += """
            AND year <= %s
        """

    copy += """
        ORDER BY emp.id
    """

    filename = "Lobbyist_Employment_History_{}.csv".format(timezone.now().isoformat())

    return make_response(copy, filename, args)


def four_oh_four(request):
    return render(request, "404.html", {}, status=404)


def five_hundred(request):
    return render(request, "500.html", {}, status=500)


def flush_cache(request):
    if request.GET.get("key") == settings.FLUSH_CACHE_KEY:
        cache.clear()
        return HttpResponse("woo!")
    else:
        return HttpResponse("Sorry, I can't do that")
