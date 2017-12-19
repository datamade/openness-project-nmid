from django.core.management.base import BaseCommand
from django.conf import settings
import sqlalchemy as sa

from camp_fin.models import Campaign, Race


DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'

engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

class Command(BaseCommand):
    help = 'Populate Races based on existing Campaigns.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recreate',
            action='store_true',
            dest='recreate',
            default=False,
            help='Drop existing Race data, and recreate it'
        )

    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS('Creating Races from Campaigns...'))

        if options['recreate']:
            with engine.connect() as conn:
                with conn.begin():
                    conn.execute('''
                        UPDATE camp_fin_campaign
                        SET active_race_id = NULL
                    ''')
                    conn.execute('''TRUNCATE camp_fin_race''')

        campaigns = Campaign.objects.all()

        num_races = 0
        num_campaigns = len(campaigns)

        for campaign in campaigns:
            kwargs = {
                'office': campaign.office,
                'office_type': campaign.office.office_type,
                'division': campaign.division,
                'district': campaign.district,
                'county': campaign.county,
                'election_season': campaign.election_season
            }

            race, created = Race.objects.get_or_create(**kwargs)

            if created:
                num_races += 1

            campaign.active_race = race
            campaign.save()

        msg = 'Created {num_races} races from {num_campaigns} campaigns!'
        self.stdout.write(self.style.SUCCESS(msg.format(num_races=num_races,
                                                        num_campaigns=num_campaigns)))
