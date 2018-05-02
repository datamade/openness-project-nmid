from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
import sqlalchemy as sa

from camp_fin.models import Campaign, Race, Candidate, Office, OfficeType


DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'
engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

class Command(BaseCommand):
    help = 'Make edits to the data sent to us in April 2018.'

    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS('Editing erroneous race data'))

        self.stdout.write(self.style.SUCCESS('Removing missing candidates...'))
        self.remove_missing_candidates()

        ################################
        # Public regulation commission #
        ################################

        self.stdout.write(self.style.SUCCESS('Fixing public regulation commission races...'))

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

        self.stdout.write(self.style.SUCCESS('Fixing state rep races...'))

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

        # Move Susan Herrera to the proper District 41
        herrera = Campaign.objects.filter(candidate__slug='susan-herrera-4187')\
                                  .filter(election_season__id='18')\
                                  .first()
        herrera.district_id = 119
        herrera.save()

        # Remove duplicate Susan Herrera
        dupe_herrera = Campaign.objects.filter(candidate__slug='susan-k-herrera-4149')\
                                .filter(election_season__id='18')\
                                .first()

        if dupe_herrera:
            dupe_herrera.delete()

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
        self.delete_campaigns_from_candidate(jamarillo)

        gallegos = Candidate.objects.get(id=4453)
        self.delete_campaigns_from_candidate(gallegos)

        white = Candidate.objects.get(id=4265)
        self.delete_campaigns_from_candidate(white)

        garcia = Candidate.objects.get(id=4315)
        self.delete_campaigns_from_candidate(garcia)

        sanchez = Candidate.objects.get(id=4314)
        self.delete_campaigns_from_candidate(sanchez)

        chandler = Candidate.objects.get(id=4141)
        self.delete_campaigns_from_candidate(chandler)

        armstrong = Candidate.objects.get(id=4360)
        self.delete_campaigns_from_candidate(armstrong)

        zamora = Candidate.objects.get(id=4190)
        self.delete_campaigns_from_candidate(zamora)

        garrett = Candidate.objects.get(id=4164)
        self.delete_campaigns_from_candidate(garrett)

        ##########
        # County #
        ##########

        self.stdout.write(self.style.SUCCESS('Fixing countywide races...'))

        # Delete duplicate campaigns
        preciado = Candidate.objects.get(id=4463)
        self.delete_campaigns_from_candidate(preciado)

        apodaca = 5789
        self.delete_campaign(apodaca)

        luchini = 5406
        self.delete_campaign(luchini)

        saint = 5473
        self.delete_campaign(saint)

        garza = 5523
        self.delete_campaign(garza)

        armijo = 5475
        self.delete_campaign(armijo)

        romero = 5539
        self.delete_campaign(romero)

        baca = 5654
        self.delete_campaign(baca)

        gg_sanchez = 5488
        self.delete_campaign(gg_sanchez)

        ferrari = 5624
        self.delete_campaign(ferrari)

        anaya = 5831
        self.delete_campaign(anaya)

        # Gonzalez dropped out
        gonzalez = Candidate.objects.get(id=4127).campaign_set.first()
        gonzalez.race_status = 'dropout'
        gonzalez.save()

        ############
        # Judicial #
        ############

        self.stdout.write(self.style.SUCCESS('Fixing judicial races...'))

        # Appellate judges

        dupe_duffy = self.get_camp_from_cand('megan-duffy-4122')

        if dupe_duffy:
            dupe_duffy.delete()

        attrep = self.get_camp_from_cand('jennifer--attrep-3623')
        attrep.county_id = 1
        attrep.save()

        kiehne = self.get_camp_from_cand('emil--kiehne-4102')
        kiehne.county_id = 1
        kiehne.save()

        bohnhoff = self.get_camp_from_cand('hank--bohnhoff-4081')
        bohnhoff.county_id = 1
        bohnhoff.save()

        positions = {
            'Position 1': ['kristina-bogardus-4108', 'stephen-french-3699'],
            'Posiiton 2': ['jacqueline-r-medina-4079', 'hank--bohnhoff-4081'],
            'Position 3': ['emil--kiehne-4102', 'briana-zamora-4088'],
            'Position 4': ['daniel-gallegos-4135', 'megan-duffy-4123'],
            'Position 5': ['jennifer--attrep-3623']
        }

        for position, candidates in positions.items():
            office_kwargs = {
                'description': 'Judge Of The Court Of Appeals, {}'.format(position),
                'office_type': OfficeType.objects.get(id=3),
                'status_id': 1,
            }

            office, created = Office.objects.get_or_create(**office_kwargs)

            for candidate in candidates:
                campaign = self.get_camp_from_cand(candidate)
                campaign.office = office
                campaign.save()

        # District judges

        dist_1_div_2 = [
            'maria-sanchez-gagne-3715'
        ]

        self.update_campaigns(dist_1_div_2, division_id=26, district_id=193, county_id=27)

        # Remove duplicate dist 1 div 2 race
        dupe_dist_1_div_2 = [5455, 5454]

        for dupe_id in dupe_dist_1_div_2:
            self.delete_campaign(dupe_id)

        dist_1_div_5 = [
            'matthew-jackson-4336',
            'jason-lidyard-4415',
        ]

        # Remove duplicate Donna Bevacqua-Young
        dupe_young = Candidate.objects.get(slug='donna-m-bevacqua-young-4107')
        self.delete_campaigns_from_candidate(dupe_young)

        self.update_campaigns(dist_1_div_5, division_id=29, district_id=193)

        conrad_perea = self.get_camp_from_cand('conrad-perea-4270')
        conrad_perea.division_id = 144
        conrad_perea.district_id = 82
        conrad_perea.save()

        dist_3_div_8 = [
            'jeanne-quintero-4304',
            'isabel-jerabek-4305',
            'richard-jacquez-3605',
            'dania-gardea-4303',
            'grace-duran-4302',
        ]

        self.update_campaigns(dist_3_div_8, division_id=83, district_id=199)

        dist_6_div_1 = [
            'tom-stewart-4335',
            'william-perkins-4330'
        ]

        self.update_campaigns(dist_6_div_1, division_id=96, district_id=202)

        dist_7_div_2 = [
            'roscoe-woods-4301',
            'shannon-murdock-4300',
        ]

        self.update_campaigns(dist_7_div_2, division_id=101, district_id=203)

        sarah_weaver = self.get_camp_from_cand('sarah-weaver-4271')
        sarah_weaver.division_id = 35
        sarah_weaver.district_id = 195
        sarah_weaver.save()

        steven_blankinship = self.get_camp_from_cand('steven-blankinship-4337')
        steven_blankinship.division_id = 41
        steven_blankinship.district_id = 196
        steven_blankinship.save()

        # Magistrate judges

        santa_fe_div_1 = [
            'jerry--gonzales-4112',
            'david-segura-345',
        ]

        self.update_campaigns(santa_fe_div_1, division_id=109)

        santa_fe_div_2 = ['jerry--gonzales-4112']

        self.update_campaigns(santa_fe_div_2, division_id=110)

        santa_fe_div_3 = [
            'samuel-sena-4113',
            'john--rysanek-4152'
        ]

        self.update_campaigns(santa_fe_div_3, division_id=136)

        santa_fe_div_4 = ['donita-sena-4431']

        self.update_campaigns(santa_fe_div_4, division_id=137)

        calicoat = self.get_camp_from_cand('kelly-calicoat-4340')
        calicoat.district_id = 109
        calicoat.save()

        # Jim Smith has multiple campaigns; get the one with the committee,
        # delete the others
        dupe_smiths = [5383, 5743]

        for dupe_id in dupe_smiths:
            self.delete_campaign(dupe_id)

        good_smith = Campaign.objects.get(id=5348)
        good_smith.district_id = 109
        good_smith.save()

        eddy_div_2 = ['dann-read-298']

        self.update_campaigns(eddy_div_2, division_id=110)

        eddy_div_3 = ['daniel-reyes-318', 'jimmy-foster-4269']

        self.update_campaigns(eddy_div_3, division_id=136)

        chaves_div_1 = ['kc-rogers-3390']

        self.update_campaigns(chaves_div_1, division_id=109)

        chaves_div_2 = ['mayna-myers-4178', 'e-fouratt-3847']

        self.update_campaigns(chaves_div_2, division_id=110)

        curry_div_1 = [
            'terry-martin-3451',
            'nicole-roybal-4418',
            'janemarie-vander-dussen-4153',
            'keith-farkas-4401'
        ]

        self.update_campaigns(curry_div_1, division_id=109)

        curry_div_2 = [
            'shaun-burns-4267',
            'stephen-whittington-3731',
            'sean-martinez-4266',
            'donald-sawyer-4412'
        ]

        self.update_campaigns(curry_div_2, division_id=110)

        lea_1 = ['craig-labree-3115']

        self.update_campaigns(lea_1, division_id=109)

        lea_2 = ['mike-stone-4472', 'willie-henry-1705']

        self.update_campaigns(lea_2, division_id=110)

        lea_3 = ['jimmie-jones-4092', 'chandler-brown-4317']

        self.update_campaigns(lea_3, division_id=136)

        lea_4 = ['david-finger-2620']

        self.update_campaigns(lea_4, division_id=137)

        dona_ana_1 = ['samantha-madrid-3273']

        self.update_campaigns(dona_ana_1, division_id=109)

        dona_ana_2 = ['linda-flores-4291']

        self.update_campaigns(dona_ana_2, division_id=110)

        dona_ana_3 = ['rebecca--duffin-4154']

        self.update_campaigns(dona_ana_3, division_id=136)

        dona_ana_4 = ['norman-osborne-3249']

        self.update_campaigns(dona_ana_4, division_id=137)

        dona_ana_5 = ['kent-wingenroth-3536']

        self.update_campaigns(dona_ana_5, division_id=113)

        dona_ana_6 = ['joel-cano-4276']

        self.update_campaigns(dona_ana_6, division_id=114)

        dona_ana_7 = ['gian-rossario-4369']

        self.update_campaigns(dona_ana_7, division_id=140)

        grant_1 = ['maurine-laney-2343', 'robert-mcdonald-4136']

        self.update_campaigns(grant_1, division_id=109)

        grant_2 = ['hector-grijalva-634']

        self.update_campaigns(grant_2, division_id=110)

        colfax_1 = ['sarah-montoya-1477', 'warren-walton-1668']

        self.update_campaigns(colfax_1, division_id=109)

        colfax_2 = ['felix-pena-539']

        self.update_campaigns(colfax_2, division_id=110)

        san_miguel_1 = ['christian-montano-3388', 'lupe-torrez-4331']

        self.update_campaigns(san_miguel_1, division_id=109)

        san_miguel_2 = ['nicholas-montoya-4292', 'melanie-rivera-1121']

        self.update_campaigns(san_miguel_2, division_id=110)

        mckinley_1 = ['johnny-greene-3820', 'april-silversmith-2504']

        self.update_campaigns(mckinley_1, division_id=109)

        mckinley_2 = ['virginia-yazzie-3567', 'robert-baca-3382']

        self.update_campaigns(mckinley_2, division_id=110)

        mckinley_3 = ['conrad-friedly-4473', 'conrad-friedly-4473']

        self.update_campaigns(mckinley_3, division_id=136)

        valencia_1 = ['tina-garcia-4399']

        self.update_campaigns(valencia_1, division_id=109)

        valencia_2 = ['john-chavez-3396', 'jennie-valdez-4361']

        self.update_campaigns(valencia_2, division_id=110)

        valencia_3 = ['john-sanchez-4318']

        self.update_campaigns(valencia_3, division_id=136)

        otero_1 = ['steve-guthrie-3997', 'ronnie-rardin-4424']

        self.update_campaigns(otero_1, division_id=109)

        otero_2 = ['wallace-anderson-4362', 'jen-garza-4363']

        self.update_campaigns(otero_2, division_id=110)

        # Move Michael Suggs from the wrong race to otero 2
        suggs = self.get_camp_from_cand('michael--suggs-4168')
        suggs.office_id = 49
        suggs.save()

        san_juan_1 = ['erich-cole-4099', 'frank-dart-4406', 'gary-mcdaniel-2786']

        self.update_campaigns(san_juan_1, division_id=109)

        san_juan_2 = ['rena-scott-3151']

        self.update_campaigns(san_juan_2, division_id=110)

        san_juan_3 = ['mark-hawkinson-1957']

        self.update_campaigns(san_juan_3, division_id=136)

        san_juan_4 = ['melvin-sam-3150', 'trudy-chase-3466']

        self.update_campaigns(san_juan_4, division_id=137)

        san_juan_5 = ['pat-cordell-3943']

        self.update_campaigns(san_juan_5, division_id=113)

        san_juan_6 = ['barry-sharer-1973']

        self.update_campaigns(san_juan_6, division_id=114)

        rio_1 = ['joseph-madrid-853']

        self.update_campaigns(rio_1, division_id=109)

        rio_2 = ['alexandra-naranjo-3402']

        self.update_campaigns(rio_2, division_id=110)

        taos_1 = ['ernest-ortega-4173', 'betty-gonzales-4287']

        self.update_campaigns(taos_1, division_id=109)

        taos_2 = ['dominic-martinez-404', 'jeff-shannon-736']

        self.update_campaigns(taos_2, division_id=110)

        lincoln_1 = ['mickie-vega-3140']

        self.update_campaigns(lincoln_1, division_id=109)

        lincoln_2 = ['katie-lund-3410']

        self.update_campaigns(lincoln_2, division_id=110)

        sandoval_1 = [
            'ann-maxwell--chavez-4256',
            'richard-aguilar-4133',
            'john-trujillo-4254',
            'daniel-stoddard-315',
            'richard-pacheco-4255',
            'cindee-orona-4257',
        ]

        self.update_campaigns(sandoval_1, division_id=109)

        sandoval_2 = ['bill-mast-4268']

        self.update_campaigns(sandoval_2, division_id=110)

        sandoval_3 = ['delilah-montano-baca-370', 'justin-garcia-4158']

        self.update_campaigns(sandoval_3, divsion_id=136)

        cibola_1 = ['larry-diaz-2007']

        self.update_campaigns(cibola_1, division_id=109)

        cibola_2 = ['johnny-valdez-2468']

        self.update_campaigns(cibola_2, division_id=110)

    def get_camp_from_cand(self, slug):
        '''
        Given a slug for a Candidate, return that Candidate's 2018 Campaign.
        '''
        return Campaign.objects.filter(candidate__slug=slug).filter(election_season__id='18').first()

    def update_campaigns(self, slugs=[], **kwargs):
        '''
        Update a set of Campaigns, represented by a list of candidate slugs.
        '''
        for slug in slugs:
            camp = self.get_camp_from_cand(slug)

            for attr, val in kwargs.items():
                setattr(camp, attr, val)

            camp.save()

    def delete_campaigns_from_candidate(self, candidate):
        '''
        Given a model instance of the type `Candidate`, delete all of its
        campaigns.
        '''
        for campaign in candidate.campaign_set.all():
            campaign.delete()

    def delete_campaign(self, campaign_id):
        '''
        Delete a model instance of the type `Campaign`, if it exists.
        '''
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            campaign.delete()
        except Campaign.DoesNotExist:
            pass

    def remove_missing_candidates(self):
        '''
        Temporary fix to prevent missing foreign keys for candidates in the campaign
        table until we can get an updated candidate table.
        '''
        with connection.cursor() as curs:
            curs.execute('''
                DELETE FROM camp_fin_campaign
                WHERE candidate_id IN (
                    SELECT DISTINCT camp.candidate_id
                    FROM camp_fin_campaign AS camp
                    LEFT JOIN camp_fin_candidate AS cand
                      ON camp.candidate_id = cand.id
                    WHERE cand.id IS NULL
                )
            ''')
