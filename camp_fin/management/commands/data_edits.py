from django.core.management.base import BaseCommand
from django.conf import settings
import sqlalchemy as sa

from camp_fin.models import Campaign, Race, Candidate


DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'
engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

class Command(BaseCommand):
    help = 'Make edits to the data sent to us in April 2018.'

    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS('Editing erroneous race data...'))

        ################################
        # Public regulation commission #
        ################################

        # Combine district 4 races
        lynda_lovejoy = Campaign.objects.get(id=5780)
        lynda_lovejoy.district_id = 27
        lynda_lovejoy.save()

        # Combine district 5 races
        district_5 = Campaign.objects.filter(district__id=128)\
                                     .filter(election_season__id=18)

        for campaign in district_5:
            campaign.district_id = 28
            campaign.save()

        # Add Jerry Partin to District 2 race
        jerry_partin = Campaign.objects.filter(candidate__slug='jerry-partin-4327')\
                                       .filter(election_season__id='18')\
                                       .first()
        jerry_partin.district_id = 25
        jerry_partin.save()

        # Add Bizzell and Hall to District 5 race
        bizzell = Campaign.objects.filter(candidate__slug='joseph-bizzell-4091')\
                                  .filter(election_season__id='18')\
                                  .first()
        bizzell.district_id = 25
        bizzell.save()

        hall = Campaign.objects.filter(candidate__slug='ben-hall-4094')\
                               .filter(election_season__id='18')\
                               .first()
        hall.district_id = 25
        hall.save()

        #############
        # State rep #
        #############

        # Move Anthony Allison to District 4
        allison = Campaign.objects.filter(candidate__slug='anthony-allison-4427')\
                                  .filter(election_season__id='18')\
                                  .first()
        allison.district_id = 72
        allison.save()

        # Move correct Susan Herrera to District 41
        herrera = Campaign.objects.filter(candidate__slug='susan-herrera-4187')\
                                  .filter(election_season__id='18')\
                                  .first()
        herrera.district_id = 119
        herrera.save()

        # Combine districts 25, 27, and 29
        # Combine district 25
        trujillo = Campaign.objects.filter(candidate__slug='christine-trujillo-2846')\
                                   .filter(election_season__id='18')\
                                   .first()
        trujillo.district_id = 101
        trujillo.save()

        # Combine district 27
        larranga = Campaign.objects.filter(candidate__slug='lorenzo-larranaga-2331')\
                                   .filter(election_season__id='18')\
                                   .first()
        larranga.district_id = 103
        larranga.save()

        martin = Campaign.objects.filter(candidate__slug='nicholas-martin-4452')\
                                 .filter(election_season__id='18')\
                                 .first()
        martin.district_id = 103
        martin.save()

        # Combine district 29
        adkins = Campaign.objects.filter(candidate__slug='david-e-adkins-3497')\
                                 .filter(election_season__id='18')\
                                 .first()
        adkins.district_id = 105
        adkins.save()

        # Delete duplicate candidates
        jamarillo = Candidate.objects.get(id=4368)
        jamarillo.delete()

        gallegos = Candidate.objects.get(id=4453)
        gallegos.delete()

        white = Candidate.objects.get(id=4265)
        white.delete()


