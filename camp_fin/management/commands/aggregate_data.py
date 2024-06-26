from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.db.utils import ProgrammingError


class Command(BaseCommand):
    help = "Import New Mexico Campaign Finance data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--recreate-views",
            dest="recreate_views",
            action="store_true",
            help="Drop and recreate materialized views. Helpful when the underlying query changes.",
        )

    def handle(self, *args, **options):
        self.makeLoanBalanceView(options["recreate_views"])
        self.makeTransactionAggregates(options["recreate_views"])
        self.stdout.write(self.style.SUCCESS("Aggregates complete!"))

    def makeTransactionAggregates(self, recreate_views):
        for interval in ["day", "week", "month"]:
            if recreate_views:
                self.executeTransaction(
                    """
                    DROP MATERIALIZED VIEW IF EXISTS contributions_by_{}
                """.format(
                        interval
                    )
                )

                self.executeTransaction(
                    """
                    DROP MATERIALIZED VIEW IF EXISTS expenditures_by_{}
                """.format(
                        interval
                    )
                )

            try:
                self.executeTransaction(
                    """
                    REFRESH MATERIALIZED VIEW contributions_by_{}
                """.format(
                        interval
                    )
                )
            except ProgrammingError:
                view = """
                    CREATE MATERIALIZED VIEW contributions_by_{0} AS (
                      SELECT
                        SUM(amount) AS amount,
                        entity_id,
                        {0}
                      FROM (
                        SELECT
                          SUM(t.amount) AS amount,
                          f.entity_id,
                          MAX(date_trunc('{0}', t.received_date)) AS {0}
                        FROM camp_fin_transaction AS t
                        JOIN camp_fin_transactiontype AS tt
                          ON t.transaction_type_id = tt.id
                        JOIN camp_fin_filing AS f
                          ON t.filing_id = f.id
                        WHERE tt.contribution = TRUE
                          AND tt.description in (
                            'Monetary Contribution',
                            'Anonymous Contribution'
                          )
                        GROUP BY f.entity_id, date_trunc('{0}', t.received_date)
                        UNION
                        SELECT
                          SUM(l.amount) AS amount,
                          f.entity_id,
                          MAX(date_trunc('{0}', l.received_date)) AS {0}
                        FROM camp_fin_loan AS l
                        JOIN camp_fin_filing AS f
                          ON l.filing_id = f.id
                        GROUP BY f.entity_id, date_trunc('{0}', l.received_date)
                      ) AS s
                      GROUP BY entity_id, {0}
                    )
                """.format(
                    interval
                )

                self.executeTransaction(view)

            try:
                self.executeTransaction(
                    """
                    REFRESH MATERIALIZED VIEW expenditures_by_{}
                """.format(
                        interval
                    )
                )
            except ProgrammingError:
                view = """
                    CREATE MATERIALIZED VIEW expenditures_by_{0} AS (
                      SELECT
                        entity_id,
                        SUM(amount) AS amount,
                        {0}
                      FROM (
                        SELECT
                          filing.entity_id,
                          SUM(e.amount) AS amount,
                          date_trunc('{0}', e.received_date) AS {0}
                        FROM camp_fin_transaction AS e
                        JOIN camp_fin_transactiontype AS tt
                          ON e.transaction_type_id = tt.id
                        JOIN camp_fin_filing AS filing
                          ON e.filing_id = filing.id
                        JOIN camp_fin_filingperiod AS fp
                          ON filing.filing_period_id = fp.id
                        WHERE tt.contribution = FALSE
                          AND filing.filed_date >= '2010-01-01'
                        GROUP BY filing.entity_id, date_trunc('{0}', e.received_date)

                        UNION

                        SELECT
                          filing.entity_id,
                          SUM(lt.amount) AS amount,
                          date_trunc('{0}', lt.transaction_date) AS {0}
                        FROM camp_fin_loantransaction AS lt
                        JOIN camp_fin_loantransactiontype AS ltt
                          ON lt.transaction_type_id = ltt.id
                        JOIN camp_fin_filing AS filing
                          ON lt.filing_id = filing.id
                        JOIN camp_fin_filingperiod AS fp
                          ON filing.filing_period_id = fp.id
                        WHERE ltt.description = 'Payment'
                          AND filing.filed_date >= '2010-01-01'
                        GROUP BY filing.entity_id, date_trunc('{0}', lt.transaction_date)
                      ) AS s
                      GROUP BY entity_id, {0}
                    )
                """.format(
                    interval
                )

                self.executeTransaction(view)

    def makeLoanBalanceView(self, recreate_views):
        if recreate_views:
            self.executeTransaction(
                """
                    DROP MATERIALIZED VIEW IF EXISTS current_loan_status
                """
            )

        try:
            self.executeTransaction(
                """
                REFRESH MATERIALIZED VIEW current_loan_status
            """,
                raise_exc=True,
            )
        except ProgrammingError:
            self.executeTransaction(
                """
                CREATE MATERIALIZED VIEW current_loan_status AS (
                  SELECT
                    loan.id AS loan_id,
                    MAX(loan.amount) AS loan_amount,
                    SUM(loantrans.amount) AS payments_made,
                    (MAX(loan.amount) - SUM(loantrans.amount)) AS outstanding_balance
                  FROM camp_fin_loan AS loan
                  JOIN camp_fin_loantransaction AS loantrans
                    ON loan.id = loantrans.loan_id
                  GROUP BY loan.id
                  HAVING ((MAX(loan.amount::numeric::money) - SUM(loantrans.amount::numeric::money)) > 0::money)
                )
            """
            )

    def executeTransaction(self, query, *args, **kwargs):
        with connections["default"].cursor() as cursor:
            with transaction.atomic():
                cursor.execute("SET local timezone to 'America/Denver'")
                if kwargs:
                    cursor.execute(query, kwargs)
                else:
                    cursor.execute(query, args)
