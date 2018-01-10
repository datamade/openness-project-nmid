import datetime
import pytz

from django.urls import resolve, reverse
from django.test import TestCase
from django.db.utils import IntegrityError
from django.db import connection
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.core.management import call_command

from camp_fin.models import (Race, Campaign, Filing, Division,
                             District, Office, OfficeType,
                             Candidate, ElectionSeason, Status,
                             Entity, PoliticalParty, FilingPeriod,
                             FilingType, County, Transaction, LoanTransaction,
                             TransactionType, LoanTransactionType, Loan)
from camp_fin.views import RacesView, RaceDetail
from camp_fin.decorators import check_date_params

class FakeTestData(TestCase):
    '''
    Set up some fake data for testing purposes.
    '''
    @classmethod
    def setUpTestData(cls):
        cls.races()

    @classmethod
    def races(cls):

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

        year = datetime.datetime.now(pytz.utc).year
        last_year = year - 1
        cls.year, cls.last_year = str(year), str(last_year)

        # Generate a timestamp from two years ago for filing dates
        two_years_ago = (datetime.datetime.now(pytz.utc) - datetime.timedelta(days=730))

        cls.election_season = ElectionSeason.objects.create(year=cls.year,
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
                                                 campaign=cls.first_campaign,
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

        contribution = TransactionType.objects.create(description='Contribution',
                                                      contribution=True,
                                                      anonymous=False)

        expenditure = TransactionType.objects.create(description='Monetary Expenditure',
                                                     contribution=False,
                                                     anonymous=False)

        cls.first_contribution = Transaction.objects.create(amount=200.0,
                                                            received_date=datetime.datetime.now(pytz.utc),
                                                            date_added=datetime.datetime.now(pytz.utc),
                                                            transaction_type=contribution,
                                                            filing=cls.first_filing)

        loan_type = LoanTransactionType.objects.create(description='Payment')

        loan = Loan.objects.create(status=status,
                                   date_added=datetime.datetime.now(pytz.utc),
                                   received_date=datetime.datetime.now(pytz.utc),
                                   amount=33.33)

        cls.loan_contribution = LoanTransaction.objects.create(loan=loan,
                                                               transaction_type=loan_type,
                                                               amount=33.33,
                                                               transaction_date=datetime.datetime.now(pytz.utc),
                                                               date_added=datetime.datetime.now(pytz.utc),
                                                               filing=cls.first_filing,
                                                               transaction_status=status)

        cls.first_expenditure = Transaction.objects.create(amount=20.0,
                                                           received_date=datetime.datetime.now(pytz.utc),
                                                           date_added=datetime.datetime.now(pytz.utc),
                                                           transaction_type=expenditure,
                                                           filing=cls.first_filing)

        cls.second_filing = Filing.objects.create(entity=second_entity,
                                                  campaign=cls.second_campaign,
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

        cls.second_contribution = Transaction.objects.create(amount=100.0,
                                                             received_date=datetime.datetime.now(pytz.utc),
                                                             date_added=datetime.datetime.now(pytz.utc),
                                                             transaction_type=contribution,
                                                             filing=cls.second_filing)

        cls.second_expenditure = Transaction.objects.create(amount=20.0,
                                                            received_date=datetime.datetime.now(pytz.utc),
                                                            date_added=datetime.datetime.now(pytz.utc),
                                                            transaction_type=expenditure,
                                                            filing=cls.second_filing)

        cls.third_filing = Filing.objects.create(entity=third_entity,
                                                 campaign=cls.third_campaign,
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

        cls.third_contribution = Transaction.objects.create(amount=0.0,
                                                            received_date=datetime.datetime.now(pytz.utc),
                                                            date_added=datetime.datetime.now(pytz.utc),
                                                            transaction_type=contribution,
                                                            filing=cls.third_filing)

        cls.third_expenditure = Transaction.objects.create(amount=0.0,
                                                           received_date=datetime.datetime.now(pytz.utc),
                                                           date_added=datetime.datetime.now(pytz.utc),
                                                           transaction_type=expenditure,
                                                           filing=cls.third_filing)

        cls.filtered_filing_period = FilingPeriod.objects.create(filing_date=two_years_ago,
                                                                 due_date=two_years_ago,
                                                                 allow_no_activity=True,
                                                                 filing_period_type=filing_type,
                                                                 exclude_from_cascading=True,
                                                                 initial_date=two_years_ago,
                                                                 email_sent_status=0,
                                                                 reminder_sent_status=0)

        cls.filtered_filing = Filing.objects.create(entity=second_entity,
                                                    campaign=cls.second_campaign,
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

        cls.filtered_contribution = Transaction.objects.create(amount=0.0,
                                                               received_date=two_years_ago,
                                                               date_added=two_years_ago,
                                                               transaction_type=contribution,
                                                               filing=cls.filtered_filing)

        cls.filtered_expenditure = Transaction.objects.create(amount=0.0,
                                                              received_date=two_years_ago,
                                                              date_added=two_years_ago,
                                                              transaction_type=expenditure,
                                                              filing=cls.third_filing)

        cls.filings = ((cls.first_filing,), (cls.second_filing, cls.filtered_filing), (cls.third_filing,))

        cls.contributions = ((cls.first_contribution, cls.loan_contribution),
                             (cls.second_contribution, cls.filtered_contribution),
                             (cls.third_contribution,))

        cls.expenditures = ((cls.first_expenditure,),
                            (cls.second_expenditure, cls.filtered_expenditure),
                            (cls.third_expenditure,))

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
        self.assertEqual(self.race.year, self.year)
        self.assertEqual(self.race.funding_period, self.last_year)

    def test_race_total_funds(self):
        self.assertEqual(self.race.total_funds, (self.first_contribution.amount +
                                                 self.loan_contribution.amount +
                                                 self.second_contribution.amount))

    def test_campaigns_by_party(self):
        parties = self.race.campaigns_by_party

        self.assertEqual(parties[0][0], 'democrat')
        self.assertEqual({camp.id for camp in parties[0][1] if hasattr(camp, 'id')},
                         {self.first_campaign.id})

        self.assertEqual(parties[1][0], 'republican')
        self.assertEqual({camp.id for camp in parties[1][1] if hasattr(camp, 'id')},
                         {self.second_campaign.id, self.third_campaign.id})

        self.assertEqual(len(parties[0][1]), len(parties[1][1]))

    def test_race_string_representation(self):
        orig_year = self.election_season.year

        self.assertEqual(str(self.race),
                         '{year} Race for test office'.format(year=orig_year))

        statewide = OfficeType.objects.create(description='Statewide')

        self.race.office_type = statewide
        self.assertEqual(str(self.race),
                         '{year} Race for test office'.format(year=orig_year))

        legislative = OfficeType.objects.create(description='Legislative')

        self.race.office_type = legislative
        self.assertEqual(str(self.race),
                         '{year} Race for first district test office'.format(year=orig_year))

        county = OfficeType.objects.create(description='County Offices')

        self.race.office_type = county
        self.assertEqual(str(self.race),
                         '{year} Race for first county test office'.format(year=orig_year))

        # Test branch where year doesn't exist
        self.election_season.year = None

        self.race.office_type = statewide
        self.assertEqual(str(self.race), 'Race for test office')

        self.race.office_type = legislative
        self.assertEqual(str(self.race), 'Race for first district test office')

        self.race.office_type = county
        self.assertEqual(str(self.race), 'Race for first county test office')

        # Clean up
        self.race.office_type = self.office_type
        self.election_season.year = orig_year

        self.race.save()


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
        for campaign, contributions in zip(self.campaigns, self.contributions):
            self.assertEqual(campaign.funds_raised(), sum(cont.amount for cont
                                                          in contributions))

    def test_campaign_funds_raised_since_date(self):
        year = str(self.filing_period.filing_date.year)
        total_funds = self.second_contribution.amount
        self.assertEqual(self.second_campaign.funds_raised(since=year), total_funds)

    def test_campaign_expenditures(self):
        for campaign, expenditures in zip(self.campaigns, self.expenditures):
            self.assertEqual(campaign.expenditures(), sum(exp.amount for exp
                                                          in expenditures))

    def test_campaign_expenditures_since_date(self):
        year = str(self.filing_period.filing_date.year)
        total_expenditures = self.second_expenditure.amount
        self.assertEqual(self.second_campaign.expenditures(since=year), total_expenditures)

    def test_campaign_is_winner(self):
        self.assertFalse(self.first_campaign.is_winner)
        self.assertFalse(self.second_campaign.is_winner)

        self.race.winner = self.first_campaign
        self.race.save()

        self.assertTrue(self.first_campaign.is_winner)
        self.assertFalse(self.second_campaign.is_winner)

    def test_campaign_cash_on_hand(self):
        for campaign, filings in zip(self.campaigns, self.filings):
            filing = filings[0]
            self.assertEqual(campaign.cash_on_hand, filing.closing_balance)

    def test_campaign_party_identifier(self):
        self.assertEqual(self.first_campaign.party_identifier, 'D')
        self.assertEqual(self.second_campaign.party_identifier, 'R')
        self.assertEqual(self.non_race_campaign.party_identifier, 'I')

    def test_campaign_share_of_funds(self):
        total = self.race.total_funds
        self.assertEqual(self.first_campaign.share_of_funds(total=total), 70)
        self.assertEqual(self.second_campaign.share_of_funds(total=total), 30)
        self.assertEqual(self.third_campaign.share_of_funds(total=total), 0)


class TestRacesView(FakeTestData):
    '''
    Test view to display contested races.
    '''
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        call_command('import_data', '--add-aggregates', '--verbosity=0')

    def test_race_view_resolves(self):
        found = resolve(reverse('races'))
        self.assertEqual(found.func.view_class, RacesView)

    def test_race_view_html(self):
        year = str(self.filing_period.due_date.year)
        response = self.client.get(reverse('races') + '?year=%s' % year
                                                    + '&type=%d' % self.office_type.id)

        html = response.content.decode('utf-8')

        self.assertIn('<title>Contested %s races in New Mexico' % year, html)
        self.assertTemplateUsed(response, 'camp_fin/races.html')

        # Check that a table is loaded
        table_list = html.split('<tr')
        self.assertTrue(len(table_list) > 2)

    def test_race_detail_view_resolves(self):
        found = resolve(reverse('race-detail', args=[self.race.id]))
        self.assertEqual(found.func.view_class, RaceDetail)

    def test_race_detail_view_html(self):
        detail_url = reverse('race-detail', args=[self.race.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        html = response.content.decode('utf-8')

        self.assertIn('<title>{year} Race for test office'.format(year=self.year), html)
        self.assertTemplateUsed(response, 'camp_fin/race-detail.html')

    def test_race_detail_view_404(self):
        pk = 0
        while pk == self.race.id:
            pk += 1
            if pk == 100:
                self.fail()  # Something's gone very wrong

        bogus_url = reverse('race-detail', args=[pk])
        response = self.client.get(bogus_url)

        self.assertEqual(response.status_code, 404)


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


class TestUtils(TestCase):
    '''
    Test utility methods.
    '''
    def test_check_date_params(self):

        @check_date_params
        def good_params(since=None):
            return

        @check_date_params
        def bad_params(since=None):
            return

        # These should pass
        good_params(since='2014')
        good_params()

        # This should fail
        with self.assertRaises(AssertionError):
            bad_params(since=234543698)
