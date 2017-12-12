import datetime
import pytz

from django.test import TestCase
from django.db.utils import IntegrityError
from camp_fin.models import (Race, Campaign, Filing, Division,
                             District, Office, OfficeType,
                             Candidate, ElectionSeason, Status,
                             Entity, PoliticalParty, FilingPeriod,
                             FilingType, County)

class TestCampaignsAndRaces(TestCase):
    @classmethod
    def setUpTestData(cls):
        first_entity = Entity.objects.create(user_id=1)
        second_entity = Entity.objects.create(user_id=2)

        first_party = PoliticalParty.objects.create(name='first party')
        second_party = PoliticalParty.objects.create(name='second party')

        cls.first_candidate = Candidate.objects.create(full_name='first candidate',
                                                       entity=first_entity)
        cls.second_candidate = Candidate.objects.create(full_name='second candidate',
                                                        entity=second_entity)

        status = Status.objects.create()

        cls.office_type = OfficeType.objects.create(description='test office type')

        cls.office = Office.objects.create(description='test office',
                                           office_type=cls.office_type,
                                           status=status)

        cls.district = District.objects.create(name='first district',
                                              office=cls.office,
                                              status=status)

        cls.division = Division.objects.create(name='first division',
                                               district=cls.district,
                                               status=status)

        cls.election_season = ElectionSeason.objects.create(year='2017',
                                                            special=False,
                                                            status=status)

        cls.county = County.objects.create(name='first county')

        cls.race = Race.objects.create(division=cls.division,
                                       district=cls.district,
                                       office=cls.office,
                                       office_type=cls.office_type,
                                       election_season=cls.election_season,
                                       county=cls.county)

        cls.first_campaign = Campaign.objects.create(candidate=cls.first_candidate,
                                                     active_race=cls.race,
                                                     election_season=cls.election_season,
                                                     office=cls.office,
                                                     date_added=datetime.datetime.now(pytz.utc),
                                                     political_party=first_party)

        cls.second_campaign = Campaign.objects.create(candidate=cls.second_candidate,
                                                      active_race=cls.race,
                                                      election_season=cls.election_season,
                                                      office=cls.office,
                                                      date_added=datetime.datetime.now(pytz.utc),
                                                      political_party=second_party)

        cls.campaigns = (cls.first_campaign, cls.second_campaign)

        filing_type = FilingType.objects.create(description='type')

        cls.filing_period = FilingPeriod.objects.create(filing_date=datetime.datetime.now(pytz.utc),
                                                    due_date=datetime.datetime.now(pytz.utc),
                                                    allow_no_activity=True,
                                                    filing_period_type=filing_type,
                                                    exclude_from_cascading=True,
                                                    initial_date=datetime.datetime.now(pytz.utc),
                                                    email_sent_status=0,
                                                    reminder_sent_status=0)

        cls.first_filing = Filing.objects.create(entity=first_entity,
                                                 filing_period=cls.filing_period,
                                                 date_added=datetime.datetime.now(pytz.utc),
                                                 date_closed=datetime.datetime.now(pytz.utc),
                                                 opening_balance=0.0,
                                                 total_contributions=100.0,
                                                 total_expenditures=20.0,
                                                 closing_balance=80.0,
                                                 final=True,
                                                 no_activity=False,
                                                 edited='0')

        cls.second_filing = Filing.objects.create(entity=second_entity,
                                                  filing_period=cls.filing_period,
                                                  date_added=datetime.datetime.now(pytz.utc),
                                                  date_closed=datetime.datetime.now(pytz.utc),
                                                  opening_balance=0.0,
                                                  total_contributions=100.0,
                                                  total_expenditures=20.0,
                                                  closing_balance=80.0,
                                                  final=True,
                                                  no_activity=False,
                                                  edited='0')

        year_ago = (datetime.datetime.now(pytz.utc) - datetime.timedelta(days=730))

        cls.filtered_filing_period = FilingPeriod.objects.create(filing_date=year_ago,
                                                    due_date=year_ago,
                                                    allow_no_activity=True,
                                                    filing_period_type=filing_type,
                                                    exclude_from_cascading=True,
                                                    initial_date=year_ago,
                                                    email_sent_status=0,
                                                    reminder_sent_status=0)

        cls.filtered_filing = Filing.objects.create(entity=second_entity,
                                                    filing_period=cls.filtered_filing_period,
                                                    date_added=year_ago,
                                                    date_closed=year_ago,
                                                    opening_balance=0.0,
                                                    total_contributions=100.0,
                                                    total_expenditures=20.0,
                                                    closing_balance=80.0,
                                                    final=True,
                                                    no_activity=False,
                                                    edited='0')

        cls.filings = ((cls.first_filing,), (cls.second_filing, cls.filtered_filing))

    def test_race_unique_constraint(self):
        with self.assertRaises(IntegrityError):
            race = Race.objects.create(division=self.division,
                                      district=self.district,
                                      office=self.office,
                                      office_type=self.office_type,
                                      election_season=self.election_season,
                                      county=self.county)

    def test_race_campaigns(self):
        self.assertEqual(set(self.race.campaigns), set(self.campaigns))

    def test_race_num_candidates(self):
        self.assertEqual(self.race.num_candidates, 2)

    def test_race_total_funds(self):
        self.assertEqual(self.race.total_funds, (self.first_filing.total_contributions +
                                                 self.second_filing.total_contributions))

    def test_campaign_funds_raised(self):
        for campaign, filing in zip(self.campaigns, self.filings):
            self.assertEqual(campaign.funds_raised(), sum(flg.total_contributions
                                                          for flg in filing))

    def test_campaign_funds_raised_since_date(self):
        year = str(self.filing_period.filing_date.year)
        total_funds = self.second_filing.total_contributions
        self.assertEqual(self.second_campaign.funds_raised(since=year), total_funds)

    def test_campaign_is_winner(self):
        self.assertFalse(self.first_campaign.is_winner)
        self.assertFalse(self.second_campaign.is_winner)

        self.race.winner = self.first_campaign
        self.race.save()

        self.assertTrue(self.first_campaign.is_winner)
        self.assertFalse(self.second_campaign.is_winner)
