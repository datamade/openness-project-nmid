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
                # our lives are much simpler if we only
                # work on final filings, so we won't even bother
                # importing amended filings
                amended = record["Amended"] != "0"
                if amended:
                    continue

                try:
                    filing = models.Filing.objects.get(
                        report_id=record["ReportID"],
                        report_version_id=record["ReportVersionID"],
                    )
                    filings_linked += 1
                except models.Filing.DoesNotExist:
                    # If there is some other final version of
                    # this report, delete it
                    models.Filing.objects.filter(
                        report_id=record["ReportID"], final=True
                    ).delete()

                    filing = self._create_filing(record)
                    filings_created += 1

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
