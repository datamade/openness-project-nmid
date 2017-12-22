import datetime
import pytz

from django.urls import resolve, reverse
from django.test import TestCase
from django.db.utils import IntegrityError
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.contrib.auth.models import User

from camp_fin.models import (Race, Campaign, Filing, Division,
                             District, Office, OfficeType,
                             Candidate, ElectionSeason, Status,
                             Entity, PoliticalParty, FilingPeriod,
                             FilingType, County)
from camp_fin.views import RacesView

class FakeTestData(TestCase):
    '''
    Set up some fake data for testing purposes.
    '''
    @classmethod
    def setUpTestData(cls):
        first_entity = Entity.objects.create(user_id=1)
        second_entity = Entity.objects.create(user_id=2)
        third_entity = Entity.objects.create(user_id=3)
        fourth_entity = Entity.objects.create(user_id=4)

        first_party = PoliticalParty.objects.create(name='Democrat')
        second_party = PoliticalParty.objects.create(name='Republican')
        third_party = PoliticalParty.objects.create(name='Green')

        cls.parties = (first_party, second_party, third_party)

        cls.first_candidate = Candidate.objects.create(first_name='first',
                                                       last_name='candidate',
                                                       entity=first_entity)

        cls.second_candidate = Candidate.objects.create(first_name='second',
                                                        last_name='candidate',
                                                        entity=second_entity)

        cls.third_candidate = Candidate.objects.create(first_name='third',
                                                       last_name='candidate',
                                                       entity=third_entity)

        # We won't use this candidate in the Race. Create it to test filtering
        cls.non_race_candidate = Candidate.objects.create(first_name='non race',
                                                          last_name='candidate',
                                                          entity=fourth_entity)

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

        cls.third_campaign = Campaign.objects.create(candidate=cls.third_candidate,
                                                     active_race=cls.race,
                                                     election_season=cls.election_season,
                                                     office=cls.office,
                                                     date_added=datetime.datetime.now(pytz.utc),
                                                     political_party=second_party)

        cls.non_race_campaign = Campaign.objects.create(candidate=cls.non_race_candidate,
                                                        election_season=cls.election_season,
                                                        office=cls.office,
                                                        date_added=datetime.datetime.now(pytz.utc),
                                                        political_party=third_party)

        cls.campaigns = [cls.first_campaign, cls.second_campaign, cls.third_campaign]

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
                                                 total_contributions=200.0,
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

        cls.third_filing = Filing.objects.create(entity=third_entity,
                                                 filing_period=cls.filing_period,
                                                 date_added=datetime.datetime.now(pytz.utc),
                                                 date_closed=datetime.datetime.now(pytz.utc),
                                                 opening_balance=0.0,
                                                 total_contributions=0.0,
                                                 total_expenditures=0.0,
                                                 closing_balance=0.0,
                                                 final=True,
                                                 no_activity=False,
                                                 edited='0')

        two_years_ago = (datetime.datetime.now(pytz.utc) - datetime.timedelta(days=730))

        cls.filtered_filing_period = FilingPeriod.objects.create(filing_date=two_years_ago,
                                                    due_date=two_years_ago,
                                                    allow_no_activity=True,
                                                    filing_period_type=filing_type,
                                                    exclude_from_cascading=True,
                                                    initial_date=two_years_ago,
                                                    email_sent_status=0,
                                                    reminder_sent_status=0)

        cls.filtered_filing = Filing.objects.create(entity=second_entity,
                                                    filing_period=cls.filtered_filing_period,
                                                    date_added=two_years_ago,
                                                    date_closed=two_years_ago,
                                                    opening_balance=0.0,
                                                    total_contributions=100.0,
                                                    total_expenditures=20.0,
                                                    closing_balance=80.0,
                                                    final=True,
                                                    no_activity=False,
                                                    edited='0')

        cls.filings = ((cls.first_filing,), (cls.second_filing, cls.filtered_filing), (cls.third_filing,))


class TestRaces(FakeTestData):
    '''
    Test the methods of the `Race` model, as well as a few desirable constraints.
    '''
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

    def test_race_sorted_campaigns(self):
        self.assertEqual(self.race.sorted_campaigns, self.campaigns)

    def test_race_num_candidates(self):
        self.assertEqual(self.race.num_candidates, 3)

    def test_race_year_and_funding_period(self):
        self.assertEqual(self.race.year, '2017')
        self.assertEqual(self.race.funding_period, '2016')

    def test_race_total_funds(self):
        self.assertEqual(self.race.total_funds, (self.first_filing.total_contributions +
                                                 self.second_filing.total_contributions))

    def test_campaigns_by_party(self):
        parties = self.race.campaigns_by_party

        self.assertEqual(parties[0][0], 'democrat')
        self.assertEqual({camp.id for camp in parties[0][1] if hasattr(camp, 'id')},
                         {self.first_campaign.id})

        self.assertEqual(parties[1][0], 'republican')
        self.assertEqual({camp.id for camp in parties[1][1] if hasattr(camp, 'id')},
                         {self.second_campaign.id, self.third_campaign.id})

        self.assertEqual(len(parties[0][1]), len(parties[1][1]))


class TestCampaigns(FakeTestData):
    '''
    Test methods of the `Campaign` model.
    '''
    def test_campaign_filings(self):
        for campaign, filing in zip(self.campaigns, self.filings):
            self.assertEqual(set(campaign.filings()), set(filing))

    def test_campaign_filings_since_date(self):
        year = str(self.filing_period.filing_date.year)
        self.assertNotIn(self.filtered_filing, self.second_campaign.filings(since=year))

    def test_campaign_funds_raised(self):
        for campaign, filing in zip(self.campaigns, self.filings):
            self.assertEqual(campaign.funds_raised(), sum(flg.total_contributions
                                                          for flg in filing))

    def test_campaign_funds_raised_since_date(self):
        year = str(self.filing_period.filing_date.year)
        total_funds = self.second_filing.total_contributions
        self.assertEqual(self.second_campaign.funds_raised(since=year), total_funds)

    def test_campaign_expenditures(self):
        for campaign, filing in zip(self.campaigns, self.filings):
            self.assertEqual(campaign.expenditures(), sum(flg.total_expenditures
                                                          for flg in filing))

    def test_campaign_expenditures_since_date(self):
        year = str(self.filing_period.filing_date.year)
        total_expenditures = self.second_filing.total_expenditures
        self.assertEqual(self.second_campaign.expenditures(since=year), total_expenditures)

    def test_campaign_is_winner(self):
        self.assertFalse(self.first_campaign.is_winner)
        self.assertFalse(self.second_campaign.is_winner)

        self.race.winner = self.first_campaign
        self.race.save()

        self.assertTrue(self.first_campaign.is_winner)
        self.assertFalse(self.second_campaign.is_winner)

    def test_campaign_cash_on_hand(self):
        for campaign in self.campaigns:
            self.assertEqual(campaign.cash_on_hand, (campaign.funds_raised() - campaign.expenditures()))

    def test_campaign_party_identifier(self):
        self.assertEqual(self.first_campaign.party_identifier, 'D')
        self.assertEqual(self.second_campaign.party_identifier, 'R')
        self.assertEqual(self.non_race_campaign.party_identifier, 'I')

    def test_campaign_share_of_total_funds(self):
        self.assertEqual(self.first_campaign.share_of_total_funds, 67)
        self.assertEqual(self.second_campaign.share_of_total_funds, 33)
        self.assertEqual(self.third_campaign.share_of_total_funds, 0)


class TestRacesView(FakeTestData):
    '''
    Test view to display contested races.
    '''
    def test_race_view_resolves(self):
        found = resolve(reverse('races'))
        self.assertEqual(found.func.view_class, RacesView)

    def test_race_view_html(self):
        year = str(self.filing_period.due_date.year)
        response = self.client.get(reverse('races') + '?year=%s' % year
                                                    + '&type=%d' % self.office_type.id)

        html = response.content.decode('utf-8')

        self.assertIn('<title>Contested 2017 races in New Mexico', html)
        self.assertTemplateUsed(response, 'camp_fin/races.html')

        # Check that a table is loaded
        table_list = html.split('<tr')
        self.assertTrue(len(table_list) > 2)


class TestAdmin(FakeTestData):
    '''
    Test some functionality of the Admin console.
    '''
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.regular_user = User.objects.create_user('reggie', 'reggie@test.com', 'pass')
        cls.admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'pass')

    def setUp(self):
        # Log in admin user
        self.client.login(username='admin', password='pass')

    def test_login_admin_user(self):
        # Log out admin user
        self.client.logout()

        # Make sure regular users can't access admin console
        self.client.login(username='reggie', password='pass')
        redirect_response = self.client.get('/admin/')

        self.assertEqual(redirect_response.status_code, 302)
        self.assertIn('/admin/login/', redirect_response.url)

        self.client.logout()

        self.client.login(username='admin', password='pass')
        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 200)

    def test_editable_models(self):
        admin_page = self.client.get('/admin/')
        html = admin_page.content.decode('utf-8')

        self.assertIn('Races', html)
        self.assertIn('Race groups', html)

    def test_race_change_list_loads(self):
        change_list = self.client.get('/admin/camp_fin/race/')
        html = change_list.content.decode('utf-8')

        relevant_fields = ('__str__', 'display_division', 'display_district',
                           'display_office', 'display_office_type', 'display_county',
                           'display_election_season')

        for field in relevant_fields:
            colname = 'class="column-{field}"'.format(field=field)
            self.assertIn(colname, html)

        table_list = html.split('<tr')

        # We created one race. With the header row, that should make for a list
        # length of 3
        self.assertEqual(len(table_list), 3)

    def test_race_edit_loads(self):
        url = reverse('admin:camp_fin_race_change', args=(self.race.id,))
        edit_page = self.client.get(url, follow=True)
        html = edit_page.content.decode('utf-8')

        self.assertEqual(edit_page.status_code, 200)

    def test_race_winner_restricted_to_foreign_keys(self):
        url = reverse('admin:camp_fin_race_change', args=(self.race.id,))
        edit_page = self.client.get(url, follow=True)
        html = edit_page.content.decode('utf-8')

        self.assertIn(str(self.first_campaign), html)
        self.assertIn(str(self.second_campaign), html)

        # We didn't add the third campaign to the race, so it shouldn't show
        # up on the editing page
        self.assertNotIn(str(self.non_race_campaign), html)

    def test_admin_search(self):
        # We can search offices
        query = '?q=office'
        base_url = reverse('admin:camp_fin_race_changelist')
        url = base_url + query
        changelist = self.client.get(url, follow=True)
        html = changelist.content.decode('utf-8')

        table_list = html.split('<tr')
        self.assertEqual(len(table_list), 3)

        # We can't search candidates (change this if we decide we can!)
        bad_query = '?q=candidate'
        bad_url = base_url + bad_query
        empty_changes = self.client.get(bad_url, follow=True)
        empty_html = empty_changes.content.decode('utf-8')

        empty_table = empty_html.split('<tr')
        self.assertEqual(len(empty_table), 1)
