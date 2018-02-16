from django.urls import resolve, reverse
from django.test import TestCase
from django.db.utils import IntegrityError
from django.contrib.auth.models import User
from django.core.management import call_command
from django.http import HttpRequest, QueryDict

from camp_fin.models import (Race, Campaign, Filing, Division,
                             District, Office, OfficeType,
                             Candidate, ElectionSeason, Status,
                             Entity, PoliticalParty, FilingPeriod,
                             FilingType, County, Transaction, LoanTransaction,
                             TransactionType, LoanTransactionType, Loan)
from camp_fin.views import RacesView, RaceDetail
from camp_fin.base_views import TransactionDownloadViewSet
from camp_fin.decorators import check_date_params
from camp_fin.templatetags.helpers import format_years
from camp_fin.tests.conftest import StatelessTestCase, DatabaseTestCase

class TestRace(StatelessTestCase):
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

    def test_race_num_candidates(self):
        self.assertEqual(self.race.num_candidates, 3)

    def test_race_year_and_funding_period(self):
        self.assertEqual(self.race.year, self.year)
        self.assertEqual(self.race.funding_period, self.last_year)

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


class TestCampaign(StatelessTestCase):
    '''
    Test methods of the `Campaign` model.
    '''
    def test_campaign_filings(self):
        for campaign, filing in zip(self.campaigns, self.filings):
            self.assertEqual(set(campaign.filings()), set(filing))

    def test_campaign_filings_since_date(self):
        year = str(self.filing_period.filing_date.year)
        self.assertNotIn(self.filtered_filing, self.second_campaign.filings(since=year))

    def test_campaign_is_winner(self):
        self.assertFalse(self.first_campaign.is_winner)
        self.assertFalse(self.second_campaign.is_winner)

        self.race.winner = self.first_campaign
        self.race.save()

        self.assertTrue(self.first_campaign.is_winner)
        self.assertFalse(self.second_campaign.is_winner)

    def test_campaign_party_identifier(self):
        self.assertEqual(self.first_campaign.party_identifier, 'D')
        self.assertEqual(self.second_campaign.party_identifier, 'R')
        self.assertEqual(self.non_race_campaign.party_identifier, 'I')


class TestRaceView(StatelessTestCase):
    '''
    Test view to display contested races.
    '''
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # We don't actually need data here; we just need the table
        call_command('import_data', '--add-aggregates', '--verbosity=0')

    def test_race_view_resolves(self):
        found = resolve(reverse('races'))
        self.assertEqual(found.func.view_class, RacesView)

    def test_race_detail_view_resolves(self):
        found = resolve(reverse('race-detail', args=[self.race.id]))
        self.assertEqual(found.func.view_class, RaceDetail)

    def test_race_detail_view_404(self):
        pk = 0
        while pk == self.race.id:
            pk += 1
            if pk == 100:
                self.fail()  # Something's gone very wrong

        bogus_url = reverse('race-detail', args=[pk])
        response = self.client.get(bogus_url)

        self.assertEqual(response.status_code, 404)


class TestAdmin(StatelessTestCase):
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

    def test_format_years(self):
        assert format_years(['2017']) == '2017'
        assert format_years(['2017', '2016', '2015']) == '2015 - 2017'
        assert format_years(['2017', '2015', '2013']) == '2013, 2015, 2017'
        assert format_years(['2017', '2015', '2014', '2013']) == '2013 - 2015, 2017'
        assert (format_years(['2019', '2017', '2016', '2015', '2013', '2012']) ==
                              '2012 - 2013, 2015 - 2017, 2019')

class TestAPI(StatelessTestCase):
    '''
    Test API endpoints.
    '''
    def setUp(self):
        self.request = HttpRequest()
        self.request.method = 'GET'

    def test_get_entity_id(self):
        '''
        Test TransactionDownloadViewSet.get_entity_id.
        '''
        for ttype in ('contributions', 'expenditures'):
            self.request.path = '/api/{ttype}/'.format(ttype=ttype)
            self.request.GET = QueryDict('candidate_id=%d' % self.first_candidate.id)

            mvset = TransactionDownloadViewSet()

            self.assertEqual(mvset.get_entity_id(self.request), self.first_entity.id)

    def test_bulk_contributions(self):
        url = '/api/bulk/contributions/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_bulk_expenditures(self):
        url = '/api/bulk/expenditures/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_bulk_candidates(self):
        url = reverse('bulk-candidates')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_bulk_pacs(self):
        url = reverse('bulk-committees')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_candidate_contributions(self):
        url = '/api/contributions/?candidate_id=1'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_candidate_expenditures(self):
        url = '/api/expenditures/?candidate_id=1'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_pac_contributions(self):
        url = '/api/contributions/?pac_id=1'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_pac_expenditures(self):
        url = '/api/expenditures/?pac_id=1'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
