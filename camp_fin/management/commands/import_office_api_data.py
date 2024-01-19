import csv
import gzip
import os
import re

from django.core.management.base import BaseCommand
from django.db.models import Max
from django.db.utils import IntegrityError
from django.utils.text import slugify

import boto3
from tqdm import tqdm
import probablepeople

from camp_fin import models


class Command(BaseCommand):
    help = """
        Import data from the New Mexico Campaign Finance System:
        https://github.com/datamade/nmid-scrapers/pull/2

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

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="file",
            help="Absolute path of CSV file to import",
            required=False,
        )

    def handle(self, *args, **options):
        if options["file"]:
            f = open(options["file"], "r")

        else:
            s3 = boto3.client("s3")

            resource_name = "offices.gz"

            with open(resource_name, "wb") as download_location:
                s3.download_fileobj(
                    os.getenv("AWS_STORAGE_BUCKET_NAME", "openness-project-nmid"),
                    resource_name,
                    download_location,
                )

            f = gzip.open(resource_name, "rt")

        try:
            reader = csv.DictReader(f)

            candidates_created = 0
            candidates_linked = 0
            candidates_skipped = 0
            campaigns = []

            for record in tqdm(reader):
                name_parts = record["CandidateName"].split(",")

                try:
                    candidate_name, _ = probablepeople.tag(
                        " ".join(
                            [name_parts[1], name_parts[0], " ".join(name_parts[2:])]
                        )
                    )
                except probablepeople.RepeatedLabelError:
                    self.stderr.write(
                        f"Could not parse candidate name {record['CandidateName']}. Skipping..."
                    )
                    candidates_skipped += 1
                    continue

                full_name = re.sub(
                    r"\s{2,}",
                    " ",
                    " ".join(
                        [
                            candidate_name.get("GivenName", ""),
                            candidate_name.get("MiddleName", "")
                            or candidate_name.get("MiddleInitial", ""),
                            candidate_name.get("Surname", ""),
                            candidate_name.get("SuffixGenerational", "")
                            or candidate_name.get("SuffixOther", ""),
                        ]
                    ),
                ).strip()

                try:
                    candidate = models.Candidate.objects.get(full_name=full_name)
                    candidates_linked += 1

                except models.Candidate.MultipleObjectsReturned:
                    candidate = models.Candidate.objects.filter(
                        full_name=full_name
                    ).first()
                    candidates_linked += 1

                except models.Candidate.DoesNotExist:
                    entity_type = self.fetch_from_cache(
                        "entity_type",
                        "Candidate",
                        models.EntityType,
                        {"description": "Candidate"},
                    )

                    entity = models.Entity.objects.create(
                        user_id=self._next_entity_id,
                        entity_type=entity_type,
                    )

                    candidate = self.fetch_from_cache(
                        "candidate",
                        full_name,
                        models.Candidate,
                        dict(
                            first_name=candidate_name.get("GivenName", None),
                            middle_name=candidate_name.get("MiddleName", None)
                            or candidate_name.get("MiddleInitial", None),
                            last_name=candidate_name.get("Surname", None),
                            suffix=candidate_name.get("SuffixGenerational", None)
                            or candidate_name.get("SuffixOther", None),
                            full_name=full_name,
                            slug=slugify(
                                " ".join(
                                    [
                                        candidate_name.get("GivenName", ""),
                                        candidate_name.get("Surname", ""),
                                    ]
                                )
                            ),
                            entity=entity,
                        ),
                    )

                    self._next_entity_id += 1

                    candidates_created += 1

                election_year = re.match(r"\d{4}", record["ElectionName"]).group(0)

                election_season = self.fetch_from_cache(
                    "election_season",
                    (election_year, False),
                    models.ElectionSeason,
                    {"year": election_year, "special": False, "status_id": 0},
                )
                office = self.fetch_from_cache(
                    "office",
                    record["OfficeName"],
                    models.Office,
                    {"description": record["OfficeName"], "status_id": 0},
                )
                office_type = self.fetch_from_cache(
                    "office_type",
                    record["JurisdictionType"],
                    models.OfficeType,
                    {"description": record["JurisdictionType"]},
                )
                political_party = self.fetch_from_cache(
                    "political_party",
                    record["Party"],
                    models.PoliticalParty,
                    {"name": record["Party"]},
                )
                district = self.fetch_from_cache(
                    "district",
                    (record["District"], office.description),
                    models.District,
                    {"name": record["District"], "office": office, "status_id": 0},
                )

                if record["Jurisdiction"]:
                    county = self.fetch_from_cache(
                        "county",
                        record["Jurisdiction"],
                        models.County,
                        {"name": record["Jurisdiction"]},
                    )
                else:
                    county = None

                campaigns.append(
                    models.Campaign(
                        election_season=election_season,
                        candidate=candidate,
                        office=office,
                        district=district,
                        county=county,
                        political_party=political_party,
                    )
                )

            models.Campaign.objects.filter(election_season__year__gte=2021).delete()
            models.Campaign.objects.bulk_create(campaigns)

        finally:
            f.close()

        self.stderr.write(
            f"Linked {candidates_linked} candidates with a campaign, created {candidates_created} candidates, skipped {candidates_skipped} candidates"
        )

    def fetch_from_cache(
        self, cache_entity, cache_key, model, model_kwargs, create=True
    ):
        deidentified_model_kwargs = {
            k: v for k, v in model_kwargs.items() if k not in ("entity", "slug")
        }

        try:
            obj = model.objects.get(**deidentified_model_kwargs)
        except model.DoesNotExist:
            obj = model.objects.create(**model_kwargs)
        except model.MultipleObjectsReturned:
            obj = model.objects.filter(**deidentified_model_kwargs).first()

        return obj
