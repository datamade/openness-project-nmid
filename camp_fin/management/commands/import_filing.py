import csv

from tqdm import tqdm

from camp_fin import models

from .utils import convert_to_float


class Command:
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
                            # we will delete this to clear out associated
                            # transactions, and the expectation it will be
                            # recreated shortly
                            previous_final.delete()

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
