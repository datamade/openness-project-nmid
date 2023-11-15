import csv
from datetime import datetime
import re

from dateutil.parser import parse
from django.core.exceptions import MultipleObjectsReturned
from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils.text import slugify

from camp_fin import models


class Command(BaseCommand):
    help = "https://docs.google.com/spreadsheets/d/1bKF74KRMXiUaWttamG0lHHh2yLTSE7ctpkm6i8wSwaM/edit?usp=sharing"

    @property
    def utcnow(self):
        if not getattr(self, "_utcnow", None):
            self._utcnow = datetime.utcnow()
        return self._utcnow

    def add_arguments(self, parser):
        parser.add_argument(
            "--entity-types",
            dest="entity_types",
            default="all",
            help="Comma separated list of entity types to import",
        )

    def handle(self, *args, **options):
        with open("_data/raw/CON_2023.csv", "r") as f:
            reader = csv.DictReader(f)
            for record in reader:
                contributor = self.make_contributor(record)
                filing = self.make_filing(record)
                contribution = self.make_contribution(record, contributor, filing)
                self.stdout.write(
                    f"{str(contributor)} - {str(filing)} - {str(contribution)}"
                )

    def make_contributor(self, record):
        state, _ = models.State.objects.get_or_create(
            postal_code=record["Contributor State"]
        )

        try:
            address = models.Address.objects.get(
                street=f"{record['Contributor Address Line 1']}{' ' + record['Contributor Address Line 2'] if record['Contributor Address Line 2'] else ''}",
                city=record["Contributor City"],
                state=state,
                zipcode=record["Contributor Zip Code"],
            )
        except models.Address.DoesNotExist:
            address = models.Address.objects.create(
                street=f"{record['Contributor Address Line 1']}{' ' + record['Contributor Address Line 2'] if record['Contributor Address Line 2'] else ''}",
                city=record["Contributor City"],
                state=state,
                zipcode=record["Contributor Zip Code"],
            )
        except:
            address = models.Address.objects.filter(
                street=f"{record['Contributor Address Line 1']}{' ' + record['Contributor Address Line 2'] if record['Contributor Address Line 2'] else ''}",
                city=record["Contributor City"],
                state=state,
                zipcode=record["Contributor Zip Code"],
            ).first()

        contact_type, _ = models.ContactType.objects.get_or_create(
            description=record["Contributor Code"]
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
            entity_ids = models.Entity.objects.aggregate(max_id=Max("user_id"))
            entity_type, _ = models.EntityType.objects.get_or_create(
                description=record["Contributor Code"][:24]
            )
            entity = models.Entity.objects.create(
                user_id=entity_ids["max_id"] + 1,
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

    def make_filing(self, record):
        if record["Report Entity Type"] == "Candidate":
            entity_type, _ = models.EntityType.objects.get_or_create(
                description="Candidate"
            )
            entity, _ = models.Entity.objects.get_or_create(
                user_id=record["OrgID"], entity_type=entity_type
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

            candidate, _ = models.Candidate.objects.get_or_create(
                prefix=record["Candidate Prefix"],
                first_name=record["Candidate First Name"],
                middle_name=record["Candidate Middle Name"],
                last_name=record["Candidate Last Name"],
                suffix=record["Candidate Suffix"],
                full_name=full_name,
                entity=entity,
                slug=slugify(
                    " ".join(
                        [record["Candidate First Name"], record["Candidate Last Name"]]
                    )
                ),
            )

            election_season, _ = models.ElectionSeason.objects.get_or_create(
                year=parse(record["Start of Period"]).date().year,
                special=False,
                status_id=0,
            )

            campaign, _ = models.Campaign.objects.get_or_create(
                committee_name=record["Committee Name"],
                candidate=candidate,
                election_season=election_season,
                date_added=self.utcnow,
                office_id=0,
                political_party_id=0,
            )

            filing_kwargs = {"entity": entity, "campaign": campaign}

        else:
            entity_type, _ = models.EntityType.objects.get_or_create(
                description=record["Report Entity Type"][:24]
            )

            entity, _ = models.Entity.objects.get_or_create(
                user_id=record["OrgID"], entity_type=entity_type
            )

            pac, _ = models.PAC.objects.get_or_create(
                name=record["Committee Name"],
                entity=entity,
                date_added=self.utcnow,
                slug=slugify(record["Committee Name"]),
            )

            filing_kwargs = {"entity": entity}

        filing_type, _ = models.FilingType.objects.get_or_create(
            description=record["Report Name"][:24],
        )

        filing_period, _ = models.FilingPeriod.objects.get_or_create(
            description=record["Report Name"],
            filing_date=parse(record["Filed Date"]).date(),
            initial_date=parse(record["Start of Period"]).date(),
            allow_no_activity=False,
            exclude_from_cascading=False,
            email_sent_status=0,
            filing_period_type=filing_type,
        )

        filing, _ = models.Filing.objects.get_or_create(
            filing_period=filing_period,
            date_added=self.utcnow,
            date_closed=parse(record["End of Period"]).date(),
            **filing_kwargs,
        )

        return filing

    def make_contribution(self, record, contributor, filing):
        if record["Contribution Type"] == "Loans Received":
            transaction_type, _ = models.LoanTransactionType.objects.get_or_create(
                description="Payment"
            )

            loan = models.Loan.objects.create(
                amount=record["Transaction Amount"],
                received_date=parse(record["Transaction Date"]).date(),
                check_number=record["Check Number"],
                status_id=0,
                date_added=self.utcnow,
                contact=contributor,
                company_name=contributor.company_name or "Not specified",
                filing=filing,
            )

            contribution = models.LoanTransaction.objects.create(
                amount=record["Transaction Amount"],
                transaction_date=parse(record["Transaction Date"]).date(),
                transaction_status_id=0,
                date_added=self.utcnow,
                loan=loan,
                filing=filing,
                transaction_type=transaction_type,
            )

        elif record["Contribution Type"] == "Special Event":
            contribution = models.SpecialEvent.objects.create(
                anonymous_contributions=record["Transaction Amount"],
                event_date=parse(record["Transaction Date"]).date(),
                admission_price=0,
                attendance=0,
                total_admissions=0,
                total_expenditures=0,
                transaction_status_id=0,
                date_added=self.utcnow,
                sponsors=contributor.company_name or "Not specified",
                filing=filing,
            )

        elif "Contribution" in record["Contribution Type"]:
            transaction_type, _ = models.TransactionType.objects.get_or_create(
                description=(
                    "Forgiven Amount"
                    if record["Contribution Type"] == "Return Contribution"
                    else "Payment"
                ),
                contribution=True,
                anonymous=False,
            )

            contribution = models.Transaction.objects.create(
                amount=record["Transaction Amount"],
                received_date=parse(record["Transaction Date"]).date(),
                check_number=record["Check Number"],
                description=record["Description"][:74],
                date_added=self.utcnow,
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
