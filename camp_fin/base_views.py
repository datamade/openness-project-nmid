import csv
from collections import namedtuple
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import connection
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.generic import DetailView, ListView, TemplateView
from rest_framework import filters, viewsets
from rest_framework.response import Response

from camp_fin.api_parts import (
    TopMoneySerializer,
    TransactionCSVRenderer,
    TransactionSerializer,
)
from camp_fin.models import PAC, Candidate, Lobbyist, Organization, Transaction
from pages.models import Page

TWENTY_TEN = timezone.make_aware(datetime(2010, 1, 1))


class Echo(object):
    def write(self, value):
        return value


class PaginatedList(ListView):
    per_page = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        paginator = Paginator(context["object_list"], self.per_page)

        page = self.request.GET.get("page")
        try:
            context["object_list"] = paginator.page(page)
        except PageNotAnInteger:
            context["object_list"] = paginator.page(1)
        except EmptyPage:
            context["object_list"] = paginator.page(paginator.num_pages)

        return context


class TransactionDetail(DetailView):
    model = Transaction

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["entity"] = None

        if context["transaction"].filing.entity.candidate_set.all():
            context["entity"] = context[
                "transaction"
            ].filing.entity.candidate_set.first()
            try:
                context["office"] = context["transaction"].filing.campaign.office
            except ObjectDoesNotExist:
                context["office"] = None
        elif context["transaction"].filing.entity.pac_set.all():
            context["entity"] = context["transaction"].filing.entity.pac_set.first()
            context["office"] = None

        context["entity_type"] = context["entity"]._meta.model_name

        if (
            context["transaction"]
            .transaction_type.description.lower()
            .endswith("contribution")
        ):
            context["transaction_type"] = "contribution"
        else:
            context["transaction_type"] = "expenditure"

        filing = context["object"].filing
        mountain_time = timezone.get_current_timezone()
        date_closed = mountain_time.normalize(
            filing.date_closed.astimezone(mountain_time)
        )

        query_params = (
            "{camp_id}_{filing_id}_{year}_{month}_{day}_{hour}{minute}{second}.pdf"
        )

        camp_id = filing.campaign_id
        if not camp_id:
            camp_id = 0

        query_params = query_params.format(
            camp_id=camp_id,
            filing_id=filing.id,
            year=date_closed.year,
            month=date_closed.month,
            day=date_closed.day,
            hour=date_closed.hour,
            minute=date_closed.minute,
            second=date_closed.second,
        )

        context["sos_link"] = "https://www.cfis.state.nm.us/docs/FPReports/{}".format(
            query_params
        )

        return context


class TransactionDownload(viewsets.ViewSet):
    """
    Some common methods for downloading Transactions as CSV.
    """

    # Viewset class attributes
    serializer_class = TransactionSerializer
    renderer_classes = (TransactionCSVRenderer,)
    allowed_methods = ["GET"]

    # Transaction download class attributes
    contribution = True
    entity_types = [(None, None, None)]

    def get_entity_id(self, request):
        """
        Given an `entity_types` tuple of (param, model, name_attr) pairs, parse URL params
        and determine which object to use for finding the entity ID.
        """
        for param, model, name_attr in self.entity_types:
            if request.GET.get(param):
                # Found a valid URL param; use this model to find the entity ID
                obj_id = request.GET.get(param)
                obj = model.objects.get(id=obj_id)
                self.entity_name = getattr(obj, name_attr)
                entity = obj.entity
                return entity.id

        # No valid URL params found; default to bulk download
        self.entity_name = "bulk"
        return None

    def transaction_query(self, entity_id=None, start_date=None, end_date=None):
        """
        Method to query transactions should be implemented on the inheriting
        class.
        """
        pass

    def list(self, request):
        """
        Generate the response to a request.
        """
        self.entity_id = self.get_entity_id(request)

        if self.contribution is True:
            ttype = "contributions"
        else:
            ttype = "expenditures"

        start_date = None
        if request.GET.get("from"):
            start_date = request.GET.get("from")

        end_date = None
        if request.GET.get("to"):
            end_date = request.GET.get("to")

        query = self.transaction_query(self.entity_id, start_date, end_date)

        cursor = connection.cursor()

        # Format args for the query
        args = [
            arg for arg in (self.entity_id, start_date, end_date) if arg is not None
        ]

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

        # Add appropriate filename and header for CSV response
        filename = "{0}-{1}-{2}.csv".format(
            ttype, slugify(self.entity_name), timezone.now().isoformat()
        )

        response["Content-Disposition"] = "attachment; filename={}".format(filename)

        return response


class LobbyistTransactionDownloadViewSet(TransactionDownload):
    """
    Base viewset for returning bulk downloads of Lobbyist contributions and
    expenditures as CSV.
    """

    # Override transaction download class attributes
    entity_types = [
        # URL param / model / attribute to use to access the entity name
        ("lobbyist_id", Lobbyist, "full_name"),
        ("organization_id", Organization, "name"),
    ]

    def transaction_query(self, entity_id=None, start_date=None, end_date=None):
        """
        Return a query corresponding to the request, either for transactions by
        lobbyist/employer or for all transactions.
        """
        # Determine whether or not this is a bulk download
        if entity_id:
            bulk = False
        else:
            bulk = True

        if self.contribution:
            ttype = "contribution"
        else:
            ttype = "expenditure"

        # Get a model instance for this download
        instance = None
        if entity_id:
            for model in (Lobbyist, Organization):
                try:
                    instance = model.objects.get(entity_id=entity_id)
                    return instance.transaction_query(
                        ttype=ttype, bulk=bulk, start_date=start_date, end_date=end_date
                    )
                except model.DoesNotExist:
                    continue
        else:
            # Use a separate query for bulk downloads
            return """
                SELECT
                    trans.id AS transaction_id,
                    report.entity_id AS entity_id,
                    entity.type AS entity_type,
                    COALESCE(trans.full_name, trans.company_name) AS name,
                    COALESCE(trans.name, '') AS recipient,
                    trans.amount,
                    COALESCE(trans.beneficiary, '') AS beneficiary,
                    COALESCE(ttype.description, '') AS type,
                    COALESCE(trans.expenditure_purpose, '') AS description,
                    trans.received_date AS date
                FROM camp_fin_lobbyistreport report
                JOIN camp_fin_lobbyisttransaction trans
                    ON trans.lobbyist_report_id = report.id
                JOIN camp_fin_lobbyisttransactiontype ttype
                    ON trans.lobbyist_transaction_type_id = ttype.id
                JOIN (
                    SELECT
                        entity_id,
                        type,
                        name
                    FROM (
                        SELECT
                            entity_id,
                            'lobbyist' AS type,
                            CONCAT_WS(' ', prefix,
                                           first_name,
                                           middle_name,
                                           last_name,
                                           suffix) AS name
                        FROM camp_fin_lobbyist
                        UNION
                        SELECT
                            entity_id,
                            'employer' AS type,
                            name
                        FROM camp_fin_organization
                    ) AS all_entities
                ) AS entity
                    USING(entity_id)
            """


class TransactionDownloadViewSet(TransactionDownload):
    """
    Base viewset for returning bulk downloads of contributions and expenditures
    as CSV.
    """

    # Override transaction download class attributes
    entity_types = [
        # URL param / model / attribute to use to access the entity name
        ("candidate_id", Candidate, "full_name"),
        ("pac_id", PAC, "name"),
    ]

    def transaction_query(self, entity_id=None, start_date=None, end_date=None):
        """
        Return a query corresponding to the request, either for transactions by
        candidate/PAC or for all transactions.
        """
        if self.contribution is True:
            contribution_bool = "TRUE"
            subj_type = "recipient"
        else:
            contribution_bool = "FALSE"
            subj_type = "spender"

        base_query = """
            SELECT
              CASE WHEN transaction.redact THEN 'Redacted by donor request'
                ELSE transaction.full_name
              END as name,
              CASE WHEN transaction.redact THEN 'Redacted by donor request' ELSE (
                transaction.address || ' ' || transaction.city || ', ' || transaction.state || ' ' || transaction.zipcode
              ) END as address,
              transaction.occupation AS occupation,
              transaction.amount,
              transaction.received_date,
              transaction.check_number,
              transaction.description,
              tt.description AS transaction_type,
              entity.*,
              f.filed_date,
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
        """.format(  # noqa
            contribution_bool=contribution_bool, subj_type=subj_type
        )

        # Add optional params
        if entity_id:
            base_query += """
                AND entity_id = %s
            """

        if start_date:
            base_query += """
                AND f.filed_date >= %s
            """

        if end_date:
            base_query += """
                AND f.filed_date <= %s
            """

        base_query += """ORDER BY transaction.received_date"""

        return base_query


class TransactionBaseViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    default_filter = {}
    queryset = Transaction.objects.filter(filing__date_added__gte=TWENTY_TEN)
    filter_backends = (filters.OrderingFilter,)

    ordering_fields = ("last_name", "amount", "received_date", "description")

    allowed_methods = ["GET"]

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.default_filter:
            queryset = queryset.filter(**self.default_filter)

        candidate_id = self.request.query_params.get("candidate_id")
        pac_id = self.request.query_params.get("pac_id")

        if candidate_id:
            queryset = queryset.filter(filing__campaign__candidate__id=candidate_id)
        elif pac_id:
            queryset = queryset.filter(filing__entity__pac__id=pac_id)

        else:
            self.entity_name = None
            return []

        if self.request.query_params.get("format") == "csv":
            entity = queryset.first().filing.entity

            if entity.candidate_set.first():
                self.entity_name = entity.candidate_set.first().full_name

            elif entity.pac_set.first():
                self.entity_name = entity.pac_set.first().name

        return queryset.order_by("-received_date")


class TopMoneyView(viewsets.ViewSet):
    def list(self, request):
        cursor = connection.cursor()

        query = """
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
                  election_season.year,
                  redact,
                  ct.description
                FROM camp_fin_transaction AS transaction
                JOIN camp_fin_transactiontype AS tt
                  ON transaction.transaction_type_id = tt.id
                JOIN camp_fin_filing AS f
                  ON transaction.filing_id = f.id
                JOIN camp_fin_campaign AS c
                  ON f.campaign_id = c.id
                JOIN camp_fin_electionseason AS election_season
                  ON c.election_season_id = election_season.id
                LEFT JOIN camp_fin_contact AS contact
                  ON transaction.contact_id = contact.id
                LEFT JOIN camp_fin_contacttype AS ct
                  ON contact.contact_type_id = ct.id
                WHERE tt.contribution = %s
                  AND year >= '2010'
                GROUP BY
                  transaction.name_prefix,
                  transaction.first_name,
                  transaction.middle_name,
                  transaction.last_name,
                  transaction.suffix,
                  transaction.company_name,
                  year,
                  redact,
                  ct.description
                ORDER BY SUM(amount) DESC
              ) AS ranked_list
              ORDER BY year DESC, amount DESC
            ) AS election_groups
            WHERE rank < 11
        """

        if self.request.GET.get("entity_type") == "pac":
            query = """
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
                      transaction.company_name,
                      transaction.redact,
                      ct.description
                    FROM camp_fin_transaction AS transaction
                    JOIN camp_fin_transactiontype AS tt
                      ON transaction.transaction_type_id = tt.id
                    JOIN camp_fin_filing AS f
                      ON transaction.filing_id = f.id
                    LEFT JOIN camp_fin_contact AS contact
                      ON transaction.contact_id = contact.id
                    LEFT JOIN camp_fin_contacttype AS ct
                      ON contact.contact_type_id = ct.id
                    WHERE tt.contribution = %s
                      AND transaction.received_date >= '2010-01-01'
                    GROUP BY
                      transaction.name_prefix,
                      transaction.first_name,
                      transaction.middle_name,
                      transaction.last_name,
                      transaction.suffix,
                      transaction.company_name,
                      transaction.redact,
                      ct.description
                    ORDER BY SUM(amount) DESC
                  ) AS ranked_list
                  ORDER BY amount DESC
                ) AS election_groups
                WHERE rank < 11
            """

        cursor.execute(query, [self.contribution])

        columns = [c[0] for c in cursor.description]
        transaction_tuple = namedtuple("Transaction", columns)

        objects = [transaction_tuple(*r) for r in cursor]

        serializer = TopMoneySerializer(objects, many=True)

        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        cursor = connection.cursor()

        query = """
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
                  election_season.year,
                  transaction.redact,
                  ct.description
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
                LEFT JOIN camp_fin_contact AS contact
                  ON transaction.contact_id = contact.id
                LEFT JOIN camp_fin_contacttype AS ct
                  ON contact.contact_type_id = ct.id
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
                  election_season.year,
                  transaction.redact,
                  ct.description
                ORDER BY SUM(amount) DESC
              ) AS ranked_list
              ORDER BY year DESC, amount DESC
            ) AS election_groups
            WHERE rank < 11
        """
        if self.request.GET.get("entity_type") == "pac":
            query = """
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
                      transaction.company_name,
                      transaction.redact,
                      ct.description
                    FROM camp_fin_transaction AS transaction
                    JOIN camp_fin_transactiontype AS tt
                      ON transaction.transaction_type_id = tt.id
                    JOIN camp_fin_filing AS f
                      ON transaction.filing_id = f.id
                    JOIN camp_fin_pac AS pac
                      ON f.entity_id = pac.entity_id
                    LEFT JOIN camp_fin_contact AS contact
                      ON transaction.contact_id = contact.id
                    LEFT JOIN camp_fin_contacttype AS ct
                      ON contact.contact_type_id = ct.id
                    WHERE tt.contribution = %s
                      AND pac.id = %s
                      AND transaction.received_date >= '2010-01-01'
                    GROUP BY
                      transaction.name_prefix,
                      transaction.first_name,
                      transaction.middle_name,
                      transaction.last_name,
                      transaction.suffix,
                      transaction.company_name,
                      transaction.redact,
                      ct.description
                    ORDER BY SUM(amount) DESC
                  ) AS ranked_list
                  ORDER BY amount DESC
                ) AS election_groups
                WHERE rank < 11
            """

        cursor.execute(query, [self.contribution, pk])

        columns = [c[0] for c in cursor.description]
        transaction_tuple = namedtuple("Transaction", columns)

        objects = [transaction_tuple(*r) for r in cursor]

        serializer = TopMoneySerializer(objects, many=True)

        return Response(serializer.data)


class TopEarnersBase(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        with connection.cursor() as cursor:
            # Top earners
            cursor.execute(
                """
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
            """
            )

            columns = [c[0] for c in cursor.description]
            transaction_tuple = namedtuple("Transaction", columns)
            top_earners_objects = [transaction_tuple(*r) for r in cursor]

        context["top_earners_objects"] = top_earners_objects

        return context


class PagesMixin(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            page = Page.objects.get(path=self.page_path)
            context["page"] = page
            for blob in page.blobs.all():
                context[blob.context_name] = blob.text
        except Page.DoesNotExist:
            context["page"] = None

        return context


def iterate_cursor(header, cursor):
    yield header

    for row in cursor:
        yield row
