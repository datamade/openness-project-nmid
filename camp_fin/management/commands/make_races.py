from django.core.management.base import BaseCommand
from django.conf import settings
import sqlalchemy as sa

from camp_fin.models import Campaign, Race


DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'

'''
Defines which attributes are relevant to consider a race "unique".
Indexed by office type.
'''
UNIQUE_RACES_MAP = {
    'Statewide': ['office', 'election_season'],
    'Legislative': ['office', 'district', 'election_season'],
    'Judicial': ['office', 'district', 'division', 'county', 'election_season'],
    'Public Regulation Commission': ['office', 'district', 'election_season'],
    'Public Education Commission': ['office', 'district', 'election_season'],
    'County Offices': ['office', 'county', 'election_season'],
    'School Board': ['office', 'county', 'district', 'election_season'],
    'None': ['office', 'county', 'election_season']
}

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

            self.stdout.write(self.style.SUCCESS('Deleting existing Race data...'))

            with engine.connect() as conn:
                with conn.begin():
                    conn.execute('''
                        UPDATE camp_fin_campaign
                        SET active_race_id = NULL
                    ''')
                    conn.execute('''TRUNCATE camp_fin_race''')

            self.stdout.write(self.style.SUCCESS('Existing data deleted!'))

        campaigns = Campaign.objects.all()

        num_races = 0
        num_campaigns = len(campaigns)

        for campaign in campaigns:

            if campaign.office.office_type:
                unique_fields = UNIQUE_RACES_MAP[campaign.office.office_type.description]
            else:
                unique_fields = UNIQUE_RACES_MAP['None']

            unique_kwargs = {field: getattr(campaign, field, None) for field in unique_fields}

            race, created = Race.objects.get_or_create(**unique_kwargs)

            kwargs = {
                'office': campaign.office,
                'office_type': campaign.office.office_type,
                'division': campaign.division,
                'district': campaign.district,
                'county': campaign.county,
                'election_season': campaign.election_season
            }

            rows_updated = Race.objects.filter(id=race.id).update(**kwargs)

            assert rows_updated == 1

            if created:
                num_races += 1

            campaign.active_race = race

            # Set any missing race statuses to 'active'
            if not campaign.race_status:
                campaign.race_status = 'active'

            campaign.save()

        msg = 'Created {num_races} races from {num_campaigns} campaigns!'
        self.stdout.write(self.style.SUCCESS(msg.format(num_races=num_races,
                                                        num_campaigns=num_campaigns)))
