import csv
import gzip
import os
import re

import boto3
import probablepeople
from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils.text import slugify
from tqdm import tqdm

from camp_fin import models

from ._cache_get_patch import cache_patch

# Monkey patch Model.objects.get with an in-memory cache to
# speed up the script while keeping things readable.
cache_patch()


class Command(BaseCommand):
    help = """
        Import data from the New Mexico Campaign Finance System:
        https://github.com/datamade/nmid-scrapers/pull/2

        Data will be retrieved from S3 unless a local CSV is specified as --file
    """

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

            models.Campaign.objects.filter(election_season__year__gte=2021).delete()

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

                except models.Candidate.DoesNotExist:
                    candidate_type, _ = models.EntityType.objects.get_or_create(
                        description="Candidate"
                    )
                    person = models.Entity.objects.create(
                        entity_type=candidate_type,
                    )

                    candidate = models.Candidate.objects.create(
                        first_name=candidate_name.get("GivenName"),
                        middle_name=(
                            candidate_name.get("MiddleName")
                            or candidate_name.get("MiddleInitial")
                        ),
                        last_name=candidate_name.get("Surname"),
                        suffix=(
                            candidate_name.get("SuffixGenerational")
                            or candidate_name.get("SuffixOther")
                        ),
                        full_name=full_name,
                        slug=slugify(
                            " ".join(
                                [
                                    candidate_name.get("GivenName", ""),
                                    candidate_name.get("Surname", ""),
                                ]
                            )
                        ),
                        entity=person,
                    )

                    candidates_created += 1

                election_year = re.match(r"\d{4}", record["ElectionName"]).group(0)

                election_season, _ = models.ElectionSeason.objects.get_or_create(
                    year=election_year, special=False, status_id=0
                )

                office_type, _ = models.OfficeType.objects.get_or_create(
                    description=record["JurisdictionType"],
                )

                office, _ = models.Office.objects.get_or_create(
                    description=record["OfficeName"],
                    status_id=0,
                    office_type=office_type,
                )

                political_party, _ = models.PoliticalParty.objects.get_or_create(
                    name=record["Party"]
                )

                district, _ = models.District.objects.get_or_create(
                    name=record["District"],
                    office=office,
                    status_id=0,
                )

                if record["Jurisdiction"]:
                    county, _ = models.County.objects.get_or_create(
                        name=record["Jurisdiction"]
                    )
                else:
                    county = None

                _, created = models.Campaign.objects.get_or_create(
                    election_season=election_season,
                    candidate=candidate,
                    office=office,
                    district=district,
                    county=county,
                    political_party=political_party,
                )

                if created:
                    candidates_created += 1

        finally:
            f.close()

        self.stderr.write(
            f"Linked {candidates_linked} candidates with a campaign, created {candidates_created} candidates, skipped {candidates_skipped} candidates"
        )
