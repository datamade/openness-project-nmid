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
        bizzell.district_id = 28
        bizzell.save()

        hall = Campaign.objects.filter(candidate__slug='ben-hall-4094')\
                               .filter(election_season__id='18')\
                               .first()
        hall.district_id = 28
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

        # Move Debbie Rodella to the proper District 41
        rodella = Campaign.objects.filter(candidate__slug='debbie-rodella-363')\
                                  .filter(election_season__id='18')\
                                  .first()
        rodella.district_id = 119
        rodella.save()

        # Remove duplicate Susan Herrera
        herrera = Campaign.objects.filter(candidate__slug='susan-k-herrera-4149')\
                                  .filter(election_season__id='18')\
                                  .first()
        herrera.delete()

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
        self.delete_campaigns(jamarillo)

        gallegos = Candidate.objects.get(id=4453)
        self.delete_campaigns(gallegos)

        white = Candidate.objects.get(id=4265)
        self.delete_campaigns(white)

        garcia = Candidate.objects.get(id=4315)
        self.delete_campaigns(garcia)

        sanchez = Candidate.objects.get(id=4314)
        self.delete_campaigns(sanchez)

        chandler = Candidate.objects.get(id=4141)
        self.delete_campaigns(chandler)

        armstrong = Candidate.objects.get(id=4360)
        self.delete_campaigns(armstrong)

        zamora = Candidate.objects.get(id=4190)
        self.delete_campaigns(zamora)

        garrett = Candidate.objects.get(id=4164)
        self.delete_campaigns(garrett)

        ##########
        # County #
        ##########

        # Delete duplicate campaigns
        preciado = Candidate.objects.get(id=4463)
        self.delete_campaigns(preciado)

        apodaca = Campaign.objects.get(id=5789)
        apodaca.delete()

        luchini = Campaign.objects.get(id=5406)
        luchini.delete()

        saint = Campaign.objects.get(id=5473)
        saint.delete()

        garza = Campaign.objects.get(id=5523)
        garza.delete()

        armijo = Campaign.objects.get(id=5475)
        armijo.delete()

        romero = Campaign.objects.get(id=5539)
        romero.delete()

        baca = Campaign.objects.get(id=5654)
        baca.delete()

        gg_sanchez = Campaign.objects.get(id=5488)
        gg_sanchez.delete()

        ferrari = Campaign.objects.get(id=5624)
        ferrari.delete()

        anaya = Campaign.objects.get(id=5831)
        anaya.delete()

        # Gonzalez dropped out
        gonzalez = Candidate.objects.get(id=4127).campaign_set.first()
        gonzalez.race_status = 'dropout'
        gonzalez.save()

    def delete_campaigns(self, candidate):
        '''
        Given a model instance of the type `Candidate`, delete all of its
        campaigns.
        '''
        for campaign in candidate.campaign_set.all():
            campaign.delete()
