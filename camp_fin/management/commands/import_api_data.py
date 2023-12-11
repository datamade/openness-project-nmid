import csv
from datetime import datetime
import gzip
from itertools import groupby
import os
import re

from dateutil.parser import parse
from django.core.exceptions import MultipleObjectsReturned
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Max, Sum
from django.utils.text import slugify

import boto3
import requests
from tqdm import tqdm

from camp_fin import models


class Command(BaseCommand):
    help = """
        Import data from the New Mexico Campaign Finance System:
        https://login.cfis.sos.state.nm.us/#/dataDownload

        Data will be retrieved from S3 unless a local CSV is specified as --file
    """

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
            "office": {},
            "party": {},
        }

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
            required=False,
        )

    def handle(self, *args, **options):
        if options["transaction_type"] not in ("EXP", "CON"):
            raise ValueError("Transaction type must be one of: EXP, CON")

        if options["file"]:
            f = open(options["file"], "r")

        else:
            s3 = boto3.client("s3")

            resource_name = f"{options['transaction_type']}_{options['year']}.gz"

            with open(resource_name, "wb") as download_location:
                s3.download_fileobj(
                    os.getenv("AWS_STORAGE_BUCKET_NAME", "openness-project-nmid"),
                    resource_name,
                    download_location,
                )

            f = gzip.open(resource_name, "rt")

        try:
            if options["transaction_type"] == "CON":
                self.import_contributions(f)

            elif options["transaction_type"] == "EXP":
                self.import_expenditures(f)

        finally:
            f.close()

        self.total_filings(options["year"])
        call_command("import_data", "--add-aggregates")

    def fetch_from_cache(self, cache_entity, cache_key, model, model_kwargs):
        try:
            return self._cache[cache_entity][cache_key]
        except KeyError:
            deidentified_model_kwargs = {
                k: v for k, v in model_kwargs.items() if k not in ("entity", "slug")
            }

            try:
                obj = model.objects.get(**deidentified_model_kwargs)
            except model.DoesNotExist:
                obj = model.objects.create(**model_kwargs)
            except model.MultipleObjectsReturned:
                obj = model.objects.filter(**deidentified_model_kwargs).first()

            self._cache[cache_entity][cache_key] = obj
            return obj

    def import_contributions(self, f):
        reader = csv.DictReader(f)

        key_func = lambda record: (record["OrgID"], record["Report Name"])
        sorted_records = sorted(reader, key=key_func)

        loans, special_events, transactions = [], [], []

        for filing_group, records in groupby(tqdm(sorted_records), key=key_func):
            for i, record in enumerate(records):
                if i == 0:
                    filing = self.make_filing(record)
                    models.LoanTransaction.objects.filter(filing=filing).delete()
                    models.SpecialEvent.objects.filter(filing=filing).delete()
                    models.Transaction.objects.filter(filing=filing).exclude(
                        transaction_type__description="Monetary Expenditure"
                    ).delete()

                contributor = self.make_contributor(record)

                if record["Contribution Type"] == "Loans Received":
                    loans.append(self.make_contribution(record, contributor, filing))

                elif record["Contribution Type"] == "Special Event":
                    special_events.append(
                        self.make_contribution(record, contributor, filing)
                    )

                elif "Contribution" in record["Contribution Type"]:
                    transactions.append(
                        self.make_contribution(record, contributor, filing)
                    )

                else:
                    self.stderr.write(
                        f"Could not determine contribution type from record: {record['Contribution Type']}"
                    )

            if len(transactions) >= 2500:
                models.Transaction.objects.bulk_create(transactions)
                transactions = []

        models.LoanTransaction.objects.bulk_create(loans)
        models.SpecialEvent.objects.bulk_create(special_events)
        models.Transaction.objects.bulk_create(transactions)

    def import_expenditures(self, f):
        reader = csv.DictReader(f)

        key_func = lambda record: (record["OrgID"], record["Report Name"])
        sorted_records = sorted(reader, key=key_func)

        expenditures = []

        for filing_group, records in groupby(tqdm(sorted_records), key=key_func):
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

                expenditures.append(self.make_contribution(record, None, filing))

            if len(expenditures) >= 2500:
                models.Transaction.objects.bulk_create(expenditures)
                expenditures = []

        models.Transaction.objects.bulk_create(expenditures)

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

                candidate = self.fetch_from_cache(
                    "candidate",
                    full_name,
                    models.Candidate,
                    dict(
                        prefix=record["Candidate Prefix"] or None,
                        first_name=record["Candidate First Name"] or None,
                        middle_name=record["Candidate Middle Name"] or None,
                        last_name=record["Candidate Last Name"] or None,
                        suffix=record["Candidate Suffix"] or None,
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

                # If an existing candidate was found, grab its entity.
                if candidate.entity.user_id != record["OrgID"]:
                    entity = candidate.entity

            else:
                try:
                    candidate = (
                        models.Candidate.objects.filter(
                            campaign__committee_name=record["Committee Name"]
                        )
                        .distinct()
                        .get()
                    )
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

            office = self.fetch_from_cache(
                "office",
                None,
                models.Office,
                dict(description="Not specified", status_id=0),
            )

            party = self.fetch_from_cache(
                "party",
                None,
                models.PoliticalParty,
                dict(name="Not specified"),
            )

            campaign = self.fetch_from_cache(
                "campaign",
                (
                    record["Committee Name"],
                    candidate.full_name,
                    election_season.year,
                ),
                models.Campaign,
                dict(
                    committee_name=record["Committee Name"],
                    candidate=candidate,
                    election_season=election_season,
                    office=office,
                    political_party=party,
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
                record["Committee Name"],
                models.PAC,
                dict(
                    name=record["Committee Name"],
                    entity=entity,
                    slug=slugify(record["Committee Name"]),
                ),
            )
            # If an existing PAC was found, grab its entity.
            if pac.entity.user_id != record["OrgID"]:
                entity = pac.entity

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
        if contributor:
            address_kwargs = dict(
                address=f"{record['Contributor Address Line 1']}{' ' + record['Contributor Address Line 2'] if record['Contributor Address Line 2'] else ''}",
                city=record["Contributor City"],
                state=record["Contributor State"],
                zipcode=record["Contributor Zip Code"],
            )

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
                    **address_kwargs,
                )

                contribution = models.LoanTransaction(
                    amount=record["Transaction Amount"],
                    transaction_date=parse(record["Transaction Date"]).date(),
                    transaction_status_id=0,
                    loan=loan,
                    filing=filing,
                    transaction_type=transaction_type,
                )

            elif record["Contribution Type"] == "Special Event":
                address_kwargs.pop("state")

                contribution = models.SpecialEvent(
                    anonymous_contributions=record["Transaction Amount"],
                    event_date=parse(record["Transaction Date"]).date(),
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

                contribution = models.Transaction(
                    amount=record["Transaction Amount"],
                    received_date=parse(record["Transaction Date"]).date(),
                    check_number=record["Check Number"],
                    description=record["Description"][:74],
                    contact=contributor,
                    full_name=contributor.full_name,
                    filing=filing,
                    transaction_type=transaction_type,
                    **address_kwargs,
                    company_name=contributor.full_name,
                    occupation=record["Contributor Occupation"],
                )

        else:
            address_kwargs = dict(
                address=f"{record['Payee Address 1']}{' ' + record['Payee Address 2'] if record['Payee Address 2'] else ''}",
                city=record["Payee City"],
                state=record["Payee State"],
                zipcode=record["Payee Zip Code"],
            )

            transaction_type = self.fetch_from_cache(
                "transaction_type",
                "Monetary Expenditure",
                models.TransactionType,
                {
                    "description": "Monetary Expenditure",
                    "contribution": False,
                    "anonymous": False,
                },
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
                received_date=parse(record["Expenditure Date"]).date(),
                description=(record["Description"] or record["Expenditure Type"])[:74],
                full_name=payee_full_name,
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
