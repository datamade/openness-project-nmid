import csv
import re

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

                # Duplicate Filings:
                # https://login.cfis.sos.state.nm.us/#/exploreDetails/mP8cXhW3dUTpRJ9Yk07LpZP4048PFnxLXRUfdOLcQk01/14/120/119/2022 (Second Primary Report) # noqa
                if record["ReportID"] in {"21785"}:
                    continue

                amended = record["Amended"] != "0"

                try:
                    filing = models.Filing.objects.get(
                        report_id=record["ReportID"],
                        report_version_id=record["ReportVersionID"],
                    )
                    filings_linked += 1
                except models.Filing.DoesNotExist:
                    if not amended:
                        try:
                            previous_final = models.Filing.objects.get(
                                report_id=record["ReportID"], final=True
                            )
                        except models.Filing.DoesNotExist:
                            pass
                        else:
                            previous_final.final = None
                            previous_final.save()

                    filing = self._create_filing(record)
                    filings_created += 1
                else:
                    if filing.final and amended:
                        # if we need to change the status of a filing from
                        # final to amended, we will delete the entire filing
                        # so as to delete any associated transactions, as we
                        # only want to associate transactions with final filings
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

        entity = models.Entity.objects.get(user_id=record["StateID"])

        url = f"https://login.cfis.sos.state.nm.us//ReportsOutput//{record['ReportFileName']}"
        final = record["Amended"] == "0" or None

        filing = models.Filing.objects.create(
            filing_period=filing_period,
            filed_date=parse_date(record["FilingEndDate"]),
            date_closed=parse_date(record["FilingEndDate"]),
            final=final,
            pdf_report=url or None,
            entity=entity,
            report_id=record["ReportID"],
            report_version_id=record["ReportVersionID"],
        )

        try:
            campaign = models.Campaign.objects.get(
                election_season__year=re.match(r"\d{4}", record["ElectionYear"]).group(
                    0
                ),
                candidate__entity=entity,
                office__description=record["OfficeName"],
                district__name=record["District"],
                county__name=record["Jurisdiction"] or None,
            )
        except models.Campaign.DoesNotExist:
            pass
        else:
            filing.campaign = campaign
            filing.save()

        return filing
