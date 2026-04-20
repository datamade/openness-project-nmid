import csv
import re
from itertools import groupby

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from tqdm import tqdm

from camp_fin import models

from .utils import parse_date


def filing_key(record):
    return (
        record["OrgID"],
        record["Report Name"],
        parse_date(record["Start of Period"]),
        parse_date(record["End of Period"]),
    )


def get_month(date_str):
    date = parse_date(date_str)
    return date.month


class Command(BaseCommand):
    help = """
        Import data from the New Mexico Campaign Finance System:
        https://login.cfis.sos.state.nm.us/#/dataDownload

        Data will be retrieved from S3 unless a local CSV is specified as --file
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = {}

    def _cached_get_or_create(self, model, **kwargs):
        key = (model, tuple(sorted(kwargs.items())))
        if key not in self._cache:
            self._cache[key], _ = model.objects.get_or_create(**kwargs)
        return self._cache[key]

    def add_arguments(self, parser):
        parser.add_argument(
            "--transaction-type",
            dest="transaction_type",
            default="CON",
            help="Type of transaction to import: CON, EXP (Default: CON)",
        )
        parser.add_argument(
            "--months",
            dest="months",
            default="1,2,3,4,5,6,7,8,9,10,11,12",
            help="Comma-separated list of months to import (Default: 1,2,3,4,5,6,7,8,9,10,11,12)",
        )
        parser.add_argument(
            "--year",
            dest="year",
            default="2023",
            help="Year to import (Default: 2023)",
        )
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            default=500,
            help="Number of transaction records to bulk create at once (Default: 500)",
        )
        parser.add_argument(
            "--file",
            dest="file",
            help="Absolute path of CSV file to import",
            required=True,
        )

    def handle(self, *args, **options):
        transaction_type = options["transaction_type"]

        if transaction_type not in ("EXP", "CON"):
            raise ValueError("Transaction type must be one of: EXP, CON")

        year = options["year"]

        self.stdout.write(f"Loading data from {transaction_type}_{year}.csv")

        months = {int(m) for m in options["months"].split(",")}
        month_string = ", ".join(str(m) for m in sorted(months))

        with open(options["file"]) as f:
            self.stdout.write(
                f"Importing transactions from filing periods beginning in months {month_string}"
            )

            if transaction_type == "CON":
                self.import_contributions(f, months, year, options["batch_size"])

            elif transaction_type == "EXP":
                self.import_expenditures(f, months, year, options["batch_size"])

            self.stdout.write(self.style.SUCCESS("Transactions imported!"))

        self.stdout.write(
            f"Totaling filings from periods beginning in months {month_string}"
        )
        self.total_filings(months)
        self.stdout.write(self.style.SUCCESS("Filings totaled!"))

        call_command("aggregate_data")

    def _records_by_filing(self, records, filing_months):
        """
        Group records by filing, then filter for filings beginning in the specified
        month/s. Note that, because transactions are organized by year, transactions
        for one filing can appear across two files, if the reporting period begins in
        one year and ends in the next. This approach will return filings beginning in
        the specified month in *any* year, so that these split cases will be covered.
        For example, consider a filing period starting in December 2023 and ending in
        February 2024. Transactions would be split across the 2023 and 2024 files. To
        get them all, you would run the December import for both 2023 and 2024.
        """
        records_in_months = filter(
            lambda x: get_month(x["Start of Period"]) in filing_months, records
        )
        return groupby(tqdm(records_in_months), key=filing_key)

    def _save_batch(self, batch):
        """
        Contributions are represented by several different types of models. Sort
        then group them by class, then save each group of records.
        """
        for cls, cls_records in groupby(
            sorted(batch, key=lambda x: str(type(x))), key=lambda x: type(x)
        ):
            cls.objects.bulk_create(cls_records)

    def import_contributions(self, f, months, year, batch_size):
        reader = csv.DictReader(f)

        n_deleted = 0
        n_imported = 0

        for _, records in self._records_by_filing(reader, months):
            batch = []
            filing = None

            with transaction.atomic():
                for i, record in enumerate(records):
                    if i == 0:
                        try:
                            filing = self._get_filing(record)
                        except ValueError:
                            break

                        filing = models.Filing.objects.select_for_update().get(
                            id=filing.id
                        )

                        # The contributions files are organized by the year
                        # of the transaction date, not the date of the
                        # filing, so transactions from the same filing can
                        # appear in multiple contribution files.
                        #
                        # We need to make sure we just clear out the
                        # contributions in a file that were purportedly made
                        # in a given year.
                        n_loans_deleted, _ = models.Loan.objects.filter(
                            filing=filing, received_date__year=year
                        ).delete()
                        n_events_deleted, _ = models.SpecialEvent.objects.filter(
                            filing=filing, event_date__year=year
                        ).delete()
                        n_transactions_deleted, _ = (
                            models.Transaction.objects.filter(
                                filing=filing, received_date__year=year
                            )
                            .exclude(
                                transaction_type__description="Monetary Expenditure"
                            )
                            .delete()
                        )

                        n_deleted += (
                            n_loans_deleted + n_events_deleted + n_transactions_deleted
                        )

                    contributor = self.make_contributor(record)

                    if (
                        record["Contribution Type"]
                        in {"Loans Received", "Special Event"}
                        or "Contribution" in record["Contribution Type"]
                    ):
                        contribution = self.make_contribution(
                            record, contributor, filing
                        )
                        batch.append(contribution)

                    else:
                        self.stderr.write(
                            f"Could not determine contribution type from record: {record['Contribution Type']}"
                        )

                    if len(batch) % batch_size == 0 and batch:
                        self._save_batch(batch)
                        n_imported += len(batch)
                        batch = []

                if batch:
                    self._save_batch(batch)
                    n_imported += len(batch)

        self.stdout.write(
            self.style.NOTICE(
                f"Deleted {n_deleted} records, created {n_imported} records"
            )
        )

    def import_expenditures(self, f, months, year, batch_size):
        reader = csv.DictReader(f)

        n_deleted = 0
        n_imported = 0

        for _, records in self._records_by_filing(reader, months):
            batch = []
            filing = None

            with transaction.atomic():
                for i, record in enumerate(records):
                    if i == 0:
                        try:
                            filing = self._get_filing(record)
                        except ValueError:
                            break

                        filing = models.Filing.objects.select_for_update().get(
                            id=filing.id
                        )

                        n_transactions, _ = models.Transaction.objects.filter(
                            filing=filing,
                            transaction_type__description="Monetary Expenditure",
                            received_date__year=year,
                        ).delete()

                        n_deleted += n_transactions

                    contribution = self.make_contribution(record, None, filing)
                    batch.append(contribution)

                    if len(batch) % batch_size == 0 and batch:
                        self._save_batch(batch)
                        n_imported += len(batch)
                        batch = []

                if batch:
                    self._save_batch(batch)
                    n_imported += len(batch)

        self.stdout.write(
            self.style.NOTICE(
                f"Deleted {n_deleted} records, created {n_imported} records"
            )
        )

    def make_contributor(self, record):
        state = self._cached_get_or_create(
            models.State, postal_code=record["Contributor State"]
        )

        address = self._cached_get_or_create(
            models.Address,
            street=(
                f"{record['Contributor Address Line 1']}"
                f"{' ' + record['Contributor Address Line 2'] if record['Contributor Address Line 2'] else ''}"
            ),
            city=record["Contributor City"],
            state=state,
            zipcode=record["Contributor Zip Code"],
        )

        contact_type = self._cached_get_or_create(
            models.ContactType, description=record["Contributor Code"]
        )

        full_name = re.sub(
            r"\s{2,}",
            " ",
            " ".join(
                [
                    record["Prefix"],
                    record["First Name"],
                    record["Middle Name"],
                    record["Last Name"],
                    record["Suffix"],
                ]
            ),
        ).strip()

        if record["Contributor Code"] not in ("Individual", "Candidate"):
            contact_kwargs = {
                "company_name": full_name,
            }

        else:
            contact_kwargs = {
                "prefix": record["Prefix"],
                "first_name": record["First Name"],
                "middle_name": record["Middle Name"],
                "last_name": record["Last Name"],
                "suffix": record["Suffix"],
                "occupation": record["Contributor Occupation"],
                "company_name": record["Contributor Employer"] or "",
                "full_name": full_name,
            }

        try:
            contact = models.Contact.objects.get(
                **contact_kwargs,
                status_id=0,
                address=address,
                contact_type=contact_type,
            )
        except models.Contact.DoesNotExist:
            entity_type = self._cached_get_or_create(
                models.EntityType, description=record["Contributor Code"][:24]
            )

            entity = models.Entity.objects.create(
                entity_type=entity_type,
            )

            contact = models.Contact.objects.create(
                **contact_kwargs,
                status_id=0,
                address=address,
                contact_type=contact_type,
                entity=entity,
            )

        return contact

    def _get_filing(self, record):
        start_date = parse_date(record["Start of Period"])
        end_date = parse_date(record["End of Period"])
        if start_date is None or end_date is None:
            raise ValueError("Record is missing 'Start of Period' or 'End of Period'")

        state_id = record["OrgID"]

        try:
            pac = models.PAC.objects.get(entity__user_id=state_id)
        except models.PAC.DoesNotExist:
            try:
                pac = models.PAC.objects.get(name=record["Committee Name"])
            except models.PAC.DoesNotExist:
                msg = f"PAC with name {record['Committee Name']} does not exist."
                self.stderr.write(msg)
                raise ValueError(msg)
            else:
                pac.entity.user_id = state_id
                pac.entity.save()

        try:
            # candidate entity
            entity = (
                models.Entity.objects.filter(candidate__campaign__committee=pac)
                .distinct()
                .get()
            )
        except models.Entity.DoesNotExist:
            # committee entity
            entity = pac.entity

        # We want to associate the transactions with the final filing
        # for a reporting period
        filings = models.Filing.objects.filter(
            filing_period__description=record["Report Name"],
            filing_period__initial_date__year=start_date.year,
            filing_period__end_date__year=end_date.year,
            final=True,
            entity=entity,
        )

        # the same person can have multiple canidate committees, so we
        # need to disambiguate which one this filing is for
        if entity.entity_type.description == "Candidate":
            filings = filings.filter(campaign__committee=pac)

        try:
            filing = filings.get()
        except models.Filing.DoesNotExist:
            raise ValueError
        except models.Filing.MultipleObjectsReturned:
            filing = filings.order_by("filed_date").last()
            filing_meta = filings.values(
                "campaign__committee__name",
                "entity",
                "filing_period__description",
                "filed_date",
                "filing_period__initial_date",
                "filing_period__end_date",
            )
            msg = (
                f"{filings.count()} filings found for PAC {pac} from record "
                f"{record}:\n{filing_meta}\n\nUsing most recent filing matching query..."  # noqa
            )
            self.stderr.write(msg)

        return filing

    def make_contribution(self, record, contributor, filing):
        if contributor:
            address_kwargs = dict(
                address=(
                    f"{record['Contributor Address Line 1']}"
                    f"{' ' + record['Contributor Address Line 2'] if record['Contributor Address Line 2'] else ''}"
                ),
                city=record["Contributor City"],
                state=record["Contributor State"],
                zipcode=record["Contributor Zip Code"],
            )

            if record["Contribution Type"] == "Loans Received":
                transaction_type = self._cached_get_or_create(
                    models.LoanTransactionType, description="Payment"
                )

                loan, _ = models.Loan.objects.get_or_create(
                    amount=record["Transaction Amount"],
                    received_date=parse_date(record["Transaction Date"]),
                    check_number=record["Check Number"],
                    status_id=0,
                    contact=contributor,
                    company_name=contributor.company_name or "",
                    filing=filing,
                    **address_kwargs,
                )

                contribution = models.LoanTransaction(
                    amount=record["Transaction Amount"],
                    transaction_date=parse_date(record["Transaction Date"]),
                    transaction_status_id=0,
                    loan=loan,
                    filing=filing,
                    transaction_type=transaction_type,
                )

            elif record["Contribution Type"] == "Special Event":
                address_kwargs.pop("state")

                contribution = models.SpecialEvent(
                    anonymous_contributions=record["Transaction Amount"],
                    event_date=parse_date(record["Transaction Date"]),
                    admission_price=0,
                    attendance=0,
                    total_admissions=0,
                    total_expenditures=0,
                    transaction_status_id=0,
                    sponsors=contributor.company_name or "Not specified",
                    filing=filing,
                    **address_kwargs,
                )

            elif "Contribution" in record["Contribution Type"]:
                if "in-kind" in record["Contribution Type"].lower():
                    description = "In-Kind Contribution"
                elif "return" in record["Contribution Type"].lower():
                    description = "Return Contribution"
                elif "anonymous" in record["Contribution Type"].lower():
                    description = "Anonymous Contribution"
                else:
                    description = "Monetary Contribution"

                transaction_type = self._cached_get_or_create(
                    models.TransactionType,
                    description=description,
                    contribution=True,
                    anonymous="anonymous" in record["Contribution Type"].lower(),
                )

                contribution = models.Transaction(
                    amount=record["Transaction Amount"],
                    received_date=parse_date(record["Transaction Date"]),
                    check_number=record["Check Number"],
                    description=record["Description"][:74],
                    contact=contributor,
                    full_name=contributor.full_name,
                    name_prefix=contributor.prefix,
                    first_name=contributor.first_name,
                    middle_name=contributor.middle_name,
                    last_name=contributor.last_name,
                    suffix=contributor.suffix,
                    filing=filing,
                    transaction_type=transaction_type,
                    company_name=contributor.company_name or "",
                    occupation=contributor.occupation,
                    **address_kwargs,
                )

        else:
            address_kwargs = dict(
                address=(
                    f"{record['Payee Address 1']}"
                    f"{' ' + record['Payee Address 2'] if record['Payee Address 2'] else ''}"
                ),
                city=record["Payee City"],
                state=record["Payee State"],
                zipcode=record["Payee Zip Code"],
            )

            transaction_type = self._cached_get_or_create(
                models.TransactionType,
                description="Monetary Expenditure",
                contribution=False,
                anonymous=False,
            )

            payee_full_name = re.sub(
                r"\s{2,}",
                " ",
                " ".join(
                    [
                        record["Payee Prefix"],
                        record["Payee First Name"],
                        record["Payee Middle Name"],
                        record["Payee Last Name"],
                        record["Payee Suffix"],
                    ]
                ),
            ).strip()

            contribution = models.Transaction(
                amount=record["Expenditure Amount"],
                received_date=parse_date(record["Expenditure Date"]),
                description=(record["Description"] or record["Expenditure Type"])[:74],
                full_name=payee_full_name,
                name_prefix=record["Payee Prefix"],
                first_name=record["Payee First Name"],
                middle_name=record["Payee Middle Name"],
                last_name=record["Payee Last Name"],
                suffix=record["Payee Suffix"],
                company_name=payee_full_name,
                filing=filing,
                transaction_type=transaction_type,
                **address_kwargs,
            )

        return contribution

    def total_filings(self, months):
        filings = list(
            tqdm(
                models.Filing.objects.filter(
                    final=True,
                    filing_period__initial_date__month__gte=min(months),
                    filing_period__initial_date__month__lte=max(months),
                ).iterator()
            )
        )

        for filing in filings:
            contributions = filing.contributions().aggregate(total=Sum("amount"))
            expenditures = filing.expenditures().aggregate(total=Sum("amount"))
            loans = filing.loans().aggregate(total=Sum("amount"))

            filing.total_contributions = contributions["total"] or 0
            filing.total_expenditures = expenditures["total"] or 0
            filing.total_loans = loans["total"] or 0

        models.Filing.objects.bulk_update(
            filings, ["total_contributions", "total_expenditures", "total_loans"]
        )
