import csv

from django.core.management.base import BaseCommand
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

            pacs_created = 0
            pacs_linked = 0
            pacs_skipped = 0

            for record in tqdm(reader):

                if not record["StateID"]:
                    pacs_skipped += 1
                    continue

                try:
                    models.PAC.objects.get(entity__user_id=record["StateID"])
                    pacs_linked += 1

                except models.PAC.DoesNotExist:
                    entity_type, _ = models.EntityType.objects.get_or_create(
                        description=record["CommitteeType"]
                    )
                    entity = models.Entity.objects.create(
                        entity_type=entity_type,
                        user_id=record["StateID"],
                    )

                    models.PAC.objects.create(
                        name=record["CommitteeName"],
                        slug=f'{slugify(record["CommitteeName"])}-{get_random_string(5)}',
                        entity=entity,
                    )

                    pacs_created += 1

        self.stderr.write(
            f"found {pacs_linked} pacs, "
            f"created {pacs_created} pacs, "
            f"skipped {pacs_skipped} pacs"
        )
