import csv
from datetime import datetime
import re

from dateutil.parser import parse
from django.core.exceptions import MultipleObjectsReturned
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Max, Sum
from django.utils.text import slugify

from tqdm import tqdm

from camp_fin import models


class Command(BaseCommand):
    help = "https://docs.google.com/spreadsheets/d/1bKF74KRMXiUaWttamG0lHHh2yLTSE7ctpkm6i8wSwaM/edit?usp=sharing"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self._next_entity_id = (
                models.Entity.objects.aggregate(max_id=Max("user_id"))["max_id"] + 1
            )
        except TypeError:
            self._next_entity_id = 1

        self._cache = {
            "state": {obj.postal_code: obj for obj in models.State.objects.iterator()},
            "contact_type": {
                obj.description: obj for obj in models.ContactType.objects.iterator()
            },
            "entity_type": {
                obj.description: obj for obj in models.EntityType.objects.iterator()
            },
            "filing_type": {
                obj.description: obj for obj in models.FilingType.objects.iterator()
            },
            "transaction_type": {
                obj.description: obj
                for obj in models.TransactionType.objects.iterator()
            },
            "loan_transaction_type": {
                obj.description: obj
                for obj in models.LoanTransactionType.objects.iterator()
            },
            "entity": {},
            "candidate": {},
            "campaign": {},
            "pac": {},
            "election_season": {},
            "filing_period": {},
            "filing": {},
            "address": {},
        }

    def add_arguments(self, parser):
        parser.add_argument(
            "--entity-types",
            dest="entity_types",
            default="all",
            help="Comma separated list of entity types to import",
        )
        parser.add_argument(
            "--source-file",
            dest="source_file",
            default="all",
            help="Path to file containing data to import",
        )

    def handle(self, *args, **options):
        with open(options["source_file"], "r") as f:
            reader = csv.DictReader(f)
            for record in tqdm(reader):
                contributor = self.make_contributor(record)
                filing = self.make_filing(record)
                contribution = self.make_contribution(record, contributor, filing)

        self.total_filings()

        call_command("import_data", "--add-aggregates")

    def fetch_from_cache(self, cache_entity, cache_key, model, model_kwargs):
        try:
            return self._cache[cache_entity][cache_key]
        except KeyError:
            try:
                obj, _ = model.objects.get_or_create(**model_kwargs)
            except model.MultipleObjectsReturned:
                obj = model.objects.filter(**model_kwargs).first()
            self._cache[cache_entity][cache_key] = obj
            return obj

    def make_contributor(self, record):
        state = self.fetch_from_cache(
            "state",
            record["Contributor State"],
            models.State,
            {"postal_code": record["Contributor State"]},
        )

        address = self.fetch_from_cache(
            "address",
            (
                f"{record['Contributor Address Line 1']}{' ' + record['Contributor Address Line 2'] if record['Contributor Address Line 2'] else ''}",
                record["Contributor City"],
                state,
                record["Contributor Zip Code"],
            ),
            models.Address,
            dict(
                street=f"{record['Contributor Address Line 1']}{' ' + record['Contributor Address Line 2'] if record['Contributor Address Line 2'] else ''}",
                city=record["Contributor City"],
                state=state,
                zipcode=record["Contributor Zip Code"],
            ),
        )

        contact_type = self.fetch_from_cache(
            "contact_type",
            record["Contributor Code"],
            models.ContactType,
            {"description": record["Contributor Code"]},
        )

        if record["Contributor Code"] == "Individual":
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

            contact_kwargs = {
                "prefix": record["Prefix"],
                "first_name": record["First Name"],
                "middle_name": record["Middle Name"],
                "last_name": record["Last Name"],
                "suffix": record["Suffix"],
                "occupation": record["Contributor Occupation"],
                "company_name": record["Contributor Employer"],
                "full_name": full_name,
            }

        else:
            # This is where the organization name is stored.
            contact_kwargs = {"full_name": record["Last Name"]}

        try:
            contact = models.Contact.objects.get(
                **contact_kwargs,
                status_id=0,
                address=address,
                contact_type=contact_type,
            )
        except models.Contact.DoesNotExist:
            entity_type = self.fetch_from_cache(
                "entity_type",
                record["Contributor Code"][:24],
                models.EntityType,
                {"description": record["Contributor Code"][:24]},
            )

            entity = models.Entity.objects.create(
                user_id=self._next_entity_id,
                entity_type=entity_type,
            )
            contact = models.Contact.objects.create(
                **contact_kwargs,
                status_id=0,
                address=address,
                contact_type=contact_type,
                entity=entity,
            )

            self._next_entity_id += 1

        return contact

    def make_filing(self, record):
        if record["Report Entity Type"] == "Candidate":
            entity_type = self.fetch_from_cache(
                "entity_type",
                "Candidate",
                models.EntityType,
                {"description": "Candidate"},
            )

            entity = self.fetch_from_cache(
                "entity",
                (record["OrgID"], "Candidate"),
                models.Entity,
                {"user_id": record["OrgID"], "entity_type": entity_type},
            )

            full_name = re.sub(
                r"\s{2,}",
                " ",
                " ".join(
                    [
                        record["Candidate Prefix"],
                        record["Candidate First Name"],
                        record["Candidate Middle Name"],
                        record["Candidate Last Name"],
                        record["Candidate Suffix"],
                    ]
                ),
            ).strip()

            candidate = self.fetch_from_cache(
                "candidate",
                entity.user_id,
                models.Candidate,
                dict(
                    prefix=record["Candidate Prefix"],
                    first_name=record["Candidate First Name"],
                    middle_name=record["Candidate Middle Name"],
                    last_name=record["Candidate Last Name"],
                    suffix=record["Candidate Suffix"],
                    full_name=full_name,
                    entity=entity,
                    slug=slugify(
                        " ".join(
                            [
                                record["Candidate First Name"],
                                record["Candidate Last Name"],
                            ]
                        )
                    ),
                ),
            )

            election_year = parse(record["Start of Period"]).date().year

            election_season = self.fetch_from_cache(
                "election_season",
                (election_year, False, 0),
                models.ElectionSeason,
                dict(
                    year=parse(record["Start of Period"]).date().year,
                    special=False,
                    status_id=0,
                ),
            )

            campaign = self.fetch_from_cache(
                "campaign",
                (record["Committee Name"], candidate.full_name, election_season.year),
                models.Campaign,
                dict(
                    committee_name=record["Committee Name"],
                    candidate=candidate,
                    election_season=election_season,
                    office_id=0,
                    political_party_id=0,
                ),
            )

            filing_kwargs = {"entity": entity, "campaign": campaign}

        else:
            entity_type = self.fetch_from_cache(
                "entity_type",
                record["Report Entity Type"][:24],
                models.EntityType,
                {"description": record["Report Entity Type"][:24]},
            )

            entity = self.fetch_from_cache(
                "entity",
                (record["OrgID"], entity_type.description),
                models.Entity,
                {"user_id": record["OrgID"], "entity_type": entity_type},
            )

            pac = self.fetch_from_cache(
                "pac",
                entity.user_id,
                models.PAC,
                dict(
                    name=record["Committee Name"],
                    entity=entity,
                    slug=slugify(record["Committee Name"]),
                ),
            )

            filing_kwargs = {"entity": entity}

        filing_type = self.fetch_from_cache(
            "filing_type",
            record["Report Name"][:24],
            models.FilingType,
            {"description": record["Report Name"][:24]},
        )

        filing_period = self.fetch_from_cache(
            "filing_period",
            (
                record["Report Name"],
                parse(record["Filed Date"]).date(),
                parse(record["Start of Period"]).date(),
                parse(record["End of Period"]).date(),
            ),
            models.FilingPeriod,
            dict(
                description=record["Report Name"],
                filing_date=parse(record["Filed Date"]).date(),
                initial_date=parse(record["Start of Period"]).date(),
                due_date=parse(record["End of Period"]).date(),
                allow_no_activity=False,
                exclude_from_cascading=False,
                email_sent_status=0,
                filing_period_type=filing_type,
            ),
        )

        filing = self.fetch_from_cache(
            "filing",
            (
                filing_kwargs["entity"].user_id,
                filing_period.id,
                parse(record["End of Period"]).date(),
            ),
            models.Filing,
            dict(
                filing_period=filing_period,
                date_closed=parse(record["End of Period"]).date(),
                final=True,
                **filing_kwargs,
            ),
        )

        return filing

    def make_contribution(self, record, contributor, filing):
        if record["Contribution Type"] == "Loans Received":
            transaction_type = self.fetch_from_cache(
                "loan_transaction_type",
                "Payment",
                models.LoanTransactionType,
                {"description": "Payment"},
            )

            loan, _ = models.Loan.objects.get_or_create(
                amount=record["Transaction Amount"],
                received_date=parse(record["Transaction Date"]).date(),
                check_number=record["Check Number"],
                status_id=0,
                contact=contributor,
                company_name=contributor.company_name or "Not specified",
                filing=filing,
            )

            contribution, _ = models.LoanTransaction.objects.get_or_create(
                amount=record["Transaction Amount"],
                transaction_date=parse(record["Transaction Date"]).date(),
                transaction_status_id=0,
                loan=loan,
                filing=filing,
                transaction_type=transaction_type,
            )

        elif record["Contribution Type"] == "Special Event":
            contribution, _ = models.SpecialEvent.objects.get_or_create(
                anonymous_contributions=record["Transaction Amount"],
                event_date=parse(record["Transaction Date"]).date(),
                admission_price=0,
                attendance=0,
                total_admissions=0,
                total_expenditures=0,
                transaction_status_id=0,
                sponsors=contributor.company_name or "Not specified",
                filing=filing,
            )

        elif "Contribution" in record["Contribution Type"]:
            transaction_type = self.fetch_from_cache(
                "transaction_type",
                "Monetary contribution",
                models.TransactionType,
                {
                    "description": "Monetary contribution",
                    "contribution": True,
                    "anonymous": False,
                },
            )

            contribution, _ = models.Transaction.objects.get_or_create(
                amount=record["Transaction Amount"],
                received_date=parse(record["Transaction Date"]).date(),
                check_number=record["Check Number"],
                description=record["Description"][:74],
                contact=contributor,
                company_name=contributor.full_name,
                full_name=contributor.full_name,
                filing=filing,
                transaction_type=transaction_type,
            )

        else:
            self.stderr.write(
                f"Could not determine contribution type from record: {record['Contribution Type']}"
            )
            contribution = None

        return contribution

    def total_filings(self):
        for filing in models.Filing.objects.iterator():
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
