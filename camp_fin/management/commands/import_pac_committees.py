import csv
import logging

from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from tqdm import tqdm

from camp_fin import models

logger = logging.getLogger(__name__)


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

            for record in tqdm(reader):

                state_id = record["StateID"]
                name = record["CommitteeName"].strip()

                # PACs are uniquely identified by their state ID, when one
                # is present. Not all PACs have a state ID, though. We'd
                # like to fall back to member ID to disambiguate PACs that
                # share a name (name alone is not reliably unique), but
                # member ID turns out not to be stable across separate CFIS
                # data pulls -- it doesn't even match between this file and
                # the pac filings file for the same committee -- so it
                # can't be used as a durable link. Fall back to name, and
                # warn on the rare case where multiple existing PACs share
                # a name, since those need manual review.
                if state_id:
                    lookup = {"entity__user_id": state_id}
                else:
                    lookup = {"name": name}

                try:
                    if state_id:
                        pac = models.PAC.objects.get(**lookup)
                    else:
                        matches = models.PAC.objects.filter(**lookup)
                        if not matches.exists():
                            raise models.PAC.DoesNotExist
                        if matches.count() > 1:
                            logger.warning(
                                f"{matches.count()} PACs named '{name}' "
                                "already exist. Using the most recently "
                                "added one. Manual review recommended."
                            )
                        pac = matches.order_by("date_added").last()

                    pacs_linked += 1

                except models.PAC.DoesNotExist:
                    entity_type, _ = models.EntityType.objects.get_or_create(
                        description=record["CommitteeType"]
                    )
                    entity = models.Entity.objects.create(
                        entity_type=entity_type,
                        user_id=state_id or None,
                    )

                    pac = models.PAC.objects.create(
                        name=name,
                        slug=f"{slugify(name)}-{get_random_string(5)}",
                        entity=entity,
                    )

                    pacs_created += 1

                pac.name = name
                pac.sos_link = "https://login.cfis.sos.state.nm.us/#/exploreCommitteeDetail/{id}".format(
                    id=record["IdNumber"]
                )
                pac.save()

        self.stderr.write(f"found {pacs_linked} pacs, created {pacs_created} pacs")
