import csv
import re
from itertools import groupby

from dateutil.parser import ParserError, parse
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils.text import slugify
from tqdm import tqdm

from camp_fin import models


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

        with open(options["file"]) as f:

            if options["transaction_type"] == "CON":
                self.import_contributions(f)

            elif options["transaction_type"] == "EXP":
                self.import_expenditures(f)

        self.total_filings(options["year"])
        call_command("aggregate_data")

    def parse_date(self, date_str):
        try:
            return parse(date_str).date()
        except (ParserError, TypeError):
            self.stderr.write(
                self.style.ERROR(f"Could not parse date from string '{date_str}'")
            )
            return None

    def import_contributions(self, f):
        reader = csv.DictReader(f)

        def key_func(record):
            return (record["OrgID"], record["Report Name"])

        for filing_group, records in groupby(tqdm(reader), key=key_func):
            for i, record in enumerate(records):
                if i == 0:
                    try:
                        filing = self.make_filing(record)
                    except ValueError:
                        continue

                    models.LoanTransaction.objects.filter(filing=filing).delete()
                    models.SpecialEvent.objects.filter(filing=filing).delete()
                    models.Transaction.objects.filter(filing=filing).exclude(
                        transaction_type__description="Monetary Expenditure"
                    ).delete()

                contributor = self.make_contributor(record)

                if record["Contribution Type"] == "Loans Received":
                    self.make_contribution(record, contributor, filing).save()

                elif record["Contribution Type"] == "Special Event":
                    self.make_contribution(record, contributor, filing).save()

                elif "Contribution" in record["Contribution Type"]:
                    self.make_contribution(record, contributor, filing).save()

                else:
                    self.stderr.write(
                        f"Could not determine contribution type from record: {record['Contribution Type']}"
                    )

    def import_expenditures(self, f):
        reader = csv.DictReader(f)

        def key_func(record):
            return (record["OrgID"], record["Report Name"])

        for filing_group, records in groupby(tqdm(reader), key=key_func):
            for i, record in enumerate(records):
                if i == 0:
                    try:
                        filing = self.make_filing(record)
                    except ValueError:
                        continue

                    models.Transaction.objects.filter(
                        filing=filing,
                        transaction_type__description="Monetary Expenditure",
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

    def make_pac(self, record, entity_type=None):

        entity_type, _ = models.EntityType.objects.get_or_create(
            description=entity_type or record["Report Entity Type"]
        )

        entity, _ = models.Entity.objects.get_or_create(
            user_id=record["OrgID"], entity_type=entity_type
        )

        pac, _ = models.PAC.objects.get_or_create(
            name=record["Committee Name"],
            entity=entity,
            slug=slugify(record["Committee Name"]),
        )

        return pac

    def make_filing(self, record):

        if not any(
            (
                self.parse_date(record["Filed Date"]),
                self.parse_date(record["End of Period"]),
            )
        ):
            raise ValueError

        if not record["Report Entity Type"]:
            self.stderr.write(
                self.style.ERROR(
                    f"Report entity type not provided. Skipping record {record}..."
                )
            )
            raise ValueError

        if record["Report Entity Type"] == "Candidate":
            # Create PAC associated with candidate
            self.make_pac(record, entity_type="Political Committee")

            candidate = self._get_candidate(record)

            transaction_date = (
                record["Transaction Date"]
                if "Transaction Date" in record
                else record["Expenditure Date"]
            )

            transaction_year = self.parse_date(transaction_date).year

            try:
                campaign = models.Campaign.objects.get(
                    candidate=candidate, election_season__year=transaction_year
                )
            except models.Campaign.DoesNotExist:
                self.stderr.write(
                    f"Could not find campaign for {candidate} in {transaction_year}"
                )

                campaign = None

            if campaign and campaign.committee_name != record["Committee Name"]:
                campaign.committee_name = record["Committee Name"]
                campaign.save()

            if campaign:
                filing_kwargs = {"entity": candidate.entity, "campaign": campaign}
            else:
                filing_kwargs = {"entity": candidate.entity}

        else:
            pac = self.make_pac(record)

            filing_kwargs = {"entity": pac.entity}

        filing_type, _ = models.FilingType.objects.get_or_create(
            description=record["Report Name"][:24]
        )

        filing_period, _ = models.FilingPeriod.objects.get_or_create(
            description=record["Report Name"],
            filing_date=(
                self.parse_date(record["Filed Date"])
                or self.parse_date(record["End of Period"])
            ),
            initial_date=self.parse_date(record["Start of Period"]),
            due_date=self.parse_date(record["End of Period"]),
            allow_no_activity=False,
            exclude_from_cascading=False,
            email_sent_status=0,
            filing_period_type=filing_type,
        )

        filing, _ = models.Filing.objects.get_or_create(
            filing_period=filing_period,
            date_closed=self.parse_date(record["End of Period"]),
            final=True,
            **filing_kwargs,
        )

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
                    received_date=self.parse_date(record["Transaction Date"]),
                    check_number=record["Check Number"],
                    status_id=0,
                    contact=contributor,
                    company_name=contributor.company_name or "",
                    filing=filing,
                    **address_kwargs,
                )

                contribution = models.LoanTransaction(
                    amount=record["Transaction Amount"],
                    transaction_date=self.parse_date(record["Transaction Date"]),
                    transaction_status_id=0,
                    loan=loan,
                    filing=filing,
                    transaction_type=transaction_type,
                )

            elif record["Contribution Type"] == "Special Event":
                address_kwargs.pop("state")

                contribution = models.SpecialEvent(
                    anonymous_contributions=record["Transaction Amount"],
                    event_date=self.parse_date(record["Transaction Date"]),
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
                    received_date=self.parse_date(record["Transaction Date"]),
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
                received_date=self.parse_date(record["Expenditure Date"]),
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
            filing_period__filing_date__year=year
        ).iterator():
            contributions = filing.contributions().aggregate(total=Sum("amount"))
            expenditures = filing.expenditures().aggregate(total=Sum("amount"))
            loans = filing.loans().aggregate(total=Sum("amount"))

            filing.total_contributions = contributions["total"] or 0
            filing.total_expenditures = expenditures["total"] or 0
            filing.total_loans = loans["total"] or 0

            filing.closing_balance = filing.opening_balance or 0 + (
                filing.total_contributions
                + filing.total_loans
                - filing.total_expenditures
            )

            filing.save()

            self.stdout.write(f"Totalled {filing}")

    def _get_candidate(self, record):

        try:
            candidate = models.Candidate.objects.get(entity__user_id=record["OrgID"])

            if any(
                [
                    record["Candidate First Name"],
                    record["Candidate Last Name"],
                ]
            ):
                full_name = re.sub(
                    r"\s{2,}",
                    " ",
                    " ".join(
                        [
                            record["Candidate First Name"],
                            record["Candidate Middle Name"],
                            record["Candidate Last Name"],
                            record["Candidate Suffix"],
                        ]
                    ),
                ).strip()

                candidate.full_name = full_name
                candidate.slug = slugify(full_name)
                candidate.first_name = record["Candidate First Name"]
                candidate.middle_name = record["Candidate Middle Name"]
                candidate.last_name = record["Candidate Last Name"]
                candidate.suffix = record["Candidate Suffix"]
                candidate.save()

        except models.Candidate.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"Could not find candidate associated with committee {record['Committee Name']}. Skipping..."
                )
            )
            raise ValueError
        except models.Candidate.MultipleObjectsReturned:
            self.stdout.write(
                self.style.ERROR(
                    f"Found more than one candidate associated with committee {record['Committee Name']}. Skipping..."
                )
            )
            raise ValueError

        return candidate
