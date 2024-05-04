import csv
import re

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from tqdm import tqdm

from camp_fin import models


class Command(BaseCommand):
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

            candidates_created = 0
            candidates_linked = 0

            models.Campaign.objects.filter(election_season__year__gte=2021).delete()

            for record in tqdm(reader):

                try:
                    pac = models.PAC.objects.get(entity__user_id=record["StateID"])
                except models.PAC.DoesNotExist:
                    entity_type, _ = models.EntityType.objects.get_or_create(
                        description="Candidate Committee",
                    )
                    entity = models.Entity.objects.create(
                        entity_type=entity_type, user_id=record["StateID"]
                    )

                    committee_name = re.split(
                        "<br>", record["PoliticalPartyCommitteeName"]
                    )[0].strip(", ")

                    pac = models.PAC.objects.create(
                        name=committee_name,
                        slug=f"{slugify(committee_name)}-{get_random_string(5)}",
                        entity=entity,
                    )

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

                try:
                    campaign = models.Campaign.objects.get(
                        election_season=election_season,
                        committee=pac,
                        office=office,
                        district=district,
                        county=county,
                        political_party=political_party,
                    )
                except models.Campaign.DoesNotExist:
                    try:
                        candidate = (
                            models.Candidate.objects.filter(
                                Q(campaign__in=pac.campaigns.all())
                                | Q(
                                    email__iexact=record["CandidateEmail"],
                                    business_phone=record["PublicPhoneNumber"],
                                )
                            )
                            .distinct()
                            .get()
                        )
                        candidates_linked += 1
                    except models.Candidate.DoesNotExist:

                        candidate_type, _ = models.EntityType.objects.get_or_create(
                            description="Candidate"
                        )
                        person = models.Entity.objects.create(
                            entity_type=candidate_type,
                        )

                        candidate = models.Candidate.objects.create(
                            full_name=record["CandidateName"],
                            slug=f'{slugify(record["CandidateName"])}-{get_random_string(5)}',
                            entity=person,
                            email=record["CandidateEmail"],
                            business_phone=record["PublicPhoneNumber"],
                        )

                        candidates_created += 1

                    campaign = models.Campaign.objects.create(
                        election_season=election_season,
                        candidate=candidate,
                        committee=pac,
                        office=office,
                        district=district,
                        county=county,
                        political_party=political_party,
                    )

                campaign.sos_link = "https://login.cfis.sos.state.nm.us/#/exploreDetails/{id}/{office_id}/{district_id}/{election_id}/{election_year}".format(  # noqa
                    id=record["IDNumber"],
                    office_id=record["OfficeId"] or "null",
                    district_id=record["DistrictId"] or "null",
                    election_id=int(float(record["ElectionId"])) or "null",
                    election_year=record["ElectionYear"] or "null",
                )

                campaign.save()

        self.stderr.write(
            f"Linked {candidates_linked} candidates with a campaign, "
            f"created {candidates_created} candidates"
        )
