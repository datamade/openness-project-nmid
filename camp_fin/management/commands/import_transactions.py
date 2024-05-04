import csv
import re
from itertools import groupby

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Sum
from tqdm import tqdm

from camp_fin import models

from .utils import parse_date


def filing_key(record):
    start_date = parse_date(record["Start of Period"])
    end_date = parse_date(record["End of Period"])

    return (
        record["OrgID"],
        record["Report Name"],
        start_date.year if start_date else None,
        end_date.year if end_date else None,
    )


class Command(BaseCommand):
    help = """
        Import data from the New Mexico Campaign Finance System:
        https://login.cfis.sos.state.nm.us/#/dataDownload

        Data will be retrieved from S3 unless a local CSV is specified as --file
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--transaction-type",
            dest="transaction_type",
            default="CON",
            help="Type of transaction to import: CON, EXP (Default: CON)",
        )
        parser.add_argument(
            "--year",
            dest="year",
            default="2023",
            help="Year to import (Default: 2023)",
        )
        parser.add_argument(
            "--file",
            dest="file",
            help="Absolute path of CSV file to import",
            required=True,
        )

    def handle(self, *args, **options):
        if options["transaction_type"] not in ("EXP", "CON"):
            raise ValueError("Transaction type must be one of: EXP, CON")

        year = options["year"]

        with open(options["file"]) as f:

            if options["transaction_type"] == "CON":
                self.import_contributions(f, year)

            elif options["transaction_type"] == "EXP":
                self.import_expenditures(f, year)

        self.total_filings(year)
        call_command("aggregate_data")

    def import_contributions(self, f, year):
        reader = csv.DictReader(f)

        for filing_group, records in groupby(tqdm(reader), key=filing_key):
            for i, record in enumerate(records):
                if i == 0:
                    try:
                        filing = self._get_filing(record)
                    except ValueError:
                        break

                    # the contributions file are organized by the year
                    # of a transaction date not the date of the
                    # filing, so transactions from the same filing can
                    # appear in multiple contribution files.
                    #
                    # we need to make sure we just clear out the
                    # contributions in a file that were purportedly made
                    # in a given year.
                    models.Loan.objects.filter(
                        filing=filing, received_date__year=year
                    ).delete()
                    models.SpecialEvent.objects.filter(
                        filing=filing, event_date__year=year
                    ).delete()
                    models.Transaction.objects.filter(
                        filing=filing, received_date__year=year
                    ).exclude(
                        transaction_type__description="Monetary Expenditure"
                    ).delete()

                contributor = self.make_contributor(record)

                if (
                    record["Contribution Type"] in {"Loans Received", "Special Event"}
                    or "Contribution" in record["Contribution Type"]
                ):
                    self.make_contribution(record, contributor, filing).save()

                else:
                    self.stderr.write(
                        f"Could not determine contribution type from record: {record['Contribution Type']}"
                    )

    def import_expenditures(self, f, year):
        reader = csv.DictReader(f)

        for filing_group, records in groupby(tqdm(reader), key=filing_key):
            for i, record in enumerate(records):
                if i == 0:
                    try:
                        filing = self._get_filing(record)
                    except ValueError:
                        break

                    models.Transaction.objects.filter(
                        filing=filing,
                        transaction_type__description="Monetary Expenditure",
                        received_date__year=year,
                    ).delete()

                self.make_contribution(record, None, filing).save()

    def make_contributor(self, record):
        state, _ = models.State.objects.get_or_create(
            postal_code=record["Contributor State"]
        )

        address, _ = models.Address.objects.get_or_create(
            street=(
                f"{record['Contributor Address Line 1']}"
                f"{' ' + record['Contributor Address Line 2'] if record['Contributor Address Line 2'] else ''}"
            ),
            city=record["Contributor City"],
            state=state,
            zipcode=record["Contributor Zip Code"],
        )

        contact_type, _ = models.ContactType.objects.get_or_create(
            description=record["Contributor Code"]
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
            entity_type, _ = models.EntityType.objects.get_or_create(
                description=record["Contributor Code"][:24]
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
            pac = models.PAC.objects.get(name=record["Committee Name"])
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
                transaction_type, _ = models.LoanTransactionType.objects.get_or_create(
                    description="Payment"
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
                transaction_type, _ = models.TransactionType.objects.get_or_create(
                    description="Monetary contribution",
                    contribution=True,
                    anonymous=False,
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

            transaction_type, _ = models.TransactionType.objects.get_or_create(
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

    def total_filings(self, year):
        for filing in models.Filing.objects.filter(
            final=True,
            filing_period__initial_date__year__lte=year,
            filing_period__end_date__year__gte=year,
        ).iterator():
            contributions = filing.contributions().aggregate(total=Sum("amount"))
            expenditures = filing.expenditures().aggregate(total=Sum("amount"))
            loans = filing.loans().aggregate(total=Sum("amount"))

            filing.total_contributions = contributions["total"] or 0
            filing.total_expenditures = expenditures["total"] or 0
            filing.total_loans = loans["total"] or 0

            filing.save()

            self.stdout.write(f"Totalled {filing}")
