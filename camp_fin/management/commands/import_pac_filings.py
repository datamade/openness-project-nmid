import csv

from django.core.management.base import BaseCommand
from tqdm import tqdm

from camp_fin import models

from .utils import convert_to_float, parse_date


class Command(BaseCommand):
    help = """
        Import data from the New Mexico Campaign Finance System:
        https://github.com/datamade/nmid-scrapers/pull/2

    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="file",
            help="Absolute path of CSV file to import",
            required=True,
        )

    def handle(self, *args, **options):
        with open(options["file"]) as f:

            reader = csv.DictReader(f)

            filings_created = 0
            filings_linked = 0

            for record in tqdm(reader):

                amended = record["Amended"] != "0"

                try:
                    filing = models.Filing.objects.get(
                        report_id=record["ReportID"],
                        report_version_id=record["ReportVersionID"],
                    )
                    filings_linked += 1
                except models.Filing.DoesNotExist:
                    filing = self._create_filing(record)
                    filings_created += 1
                else:
                    if filing.final and amended:
                        # if we need to change the status of a filing from
                        # final to amended, we will delete the entire filing
                        # so as to delete any associated transactions
                        filing.delete()
                        filing = self._create_filing(record)

                if record["opening_balance"]:
                    filing.opening_balance = convert_to_float(record["opening_balance"])
                    filing.closing_balance = convert_to_float(record["closing_balance"])
                    filing.total_loans = convert_to_float(record["total_loans"])
                    filing.total_unpaid_debts = convert_to_float(record["unpaid_debt"])
                    filing.total_inkind = convert_to_float(record["total_inkind"])

                    filing.save()

        self.stderr.write(
            f"found {filings_linked} filings, " f"created {filings_created} filings, "
        )

    def _create_filing(self, record):

        filing_type, _ = models.FilingType.objects.get_or_create(
            description=record["ReportName"][:24]
        )

        filing_period, _ = models.FilingPeriod.objects.get_or_create(
            description=record["ReportName"],
            initial_date=parse_date(record["FilingStartDate"]),
            end_date=parse_date(record["FilingEndDate"]),
            due_date=parse_date(record["FilingDueDate"]),
            allow_no_activity=False,
            exclude_from_cascading=False,
            email_sent_status=0,
            filing_period_type=filing_type,
        )

        state_id = record["StateID"]
        if state_id:
            entity = models.Entity.objects.get(user_id=state_id)

        else:
            entity = models.PAC.objects.get(name=record["CommitteeName"]).entity

        url = f"https://login.cfis.sos.state.nm.us//ReportsOutput//{record['ReportFileName']}"
        final = record["Amended"] == "0" or None

        filing = models.Filing.objects.create(
            filing_period=filing_period,
            filed_date=parse_date(record["FilingEndDate"]),
            date_closed=parse_date(record["FilingEndDate"]),
            entity=entity,
            final=final,
            pdf_report=url or None,
            report_id=record["ReportID"],
            report_version_id=record["ReportVersionID"],
        )

        return filing
