from camp_fin.tests.conftest import DatabaseTestCase
from django.urls import reverse

class TestRace(DatabaseTestCase):
    '''
    Test methods of the Race class that require database access.
    '''
    def test_race_total_funds(self):
        self.assertEqual(self.race.total_funds, (self.first_contribution.amount +
                                                 self.loan.amount +
                                                 self.second_contribution.amount))

    def test_race_sorted_campaigns(self):
        self.assertEqual(self.race.sorted_campaigns, self.campaigns)

    def test_campaigns_by_party(self):
        parties = self.race.campaigns_by_party

        self.assertEqual(parties[0][0], 'democrat')
        self.assertEqual({camp.id for camp in parties[0][1] if hasattr(camp, 'id')},
                         {self.first_campaign.id})

        self.assertEqual(parties[1][0], 'republican')
        self.assertEqual({camp.id for camp in parties[1][1] if hasattr(camp, 'id')},
                         {self.second_campaign.id, self.third_campaign.id})

        self.assertEqual(len(parties[0][1]), len(parties[1][1]))


class TestCampaign(DatabaseTestCase):
    '''
    Test methods of the Campaign model that require database access.
    '''
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

    def test_campaign_cash_on_hand(self):
        for campaign, filings in zip(self.campaigns, self.filings):
            filing = filings[0]
            self.assertEqual(campaign.cash_on_hand, filing.closing_balance)

    def test_campaign_share_of_funds(self):
        total = self.race.total_funds
        self.assertEqual(self.first_campaign.share_of_funds(total=total), 70)
        self.assertEqual(self.second_campaign.share_of_funds(total=total), 30)
        self.assertEqual(self.third_campaign.share_of_funds(total=total), 0)


class TestRaceView(DatabaseTestCase):
    '''
    Test views of the Race class that require database access.
    '''
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

    def test_race_detail_view_html(self):
        detail_url = reverse('race-detail', args=[self.race.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        html = response.content.decode('utf-8')

        self.assertIn('<title>{year} Race for test office'.format(year=self.year), html)
        self.assertTemplateUsed(response, 'camp_fin/race-detail.html')
