from camp_fin.tests.conftest import DatabaseTestCase


class TestRace(DatabaseTestCase):
    """
    Test methods of the Race class that require database access.
    """

    def test_race_total_funds(self):
        self.assertEqual(
            self.race.total_funds,
            (
                self.first_contribution.amount
                + self.loan.amount
                + self.second_contribution.amount
            ),
        )

    def test_race_sorted_campaigns(self):
        self.assertEqual(self.race.sorted_campaigns, self.campaigns)

    def test_campaigns_by_party(self):
        parties = self.race.campaigns_by_party

        self.assertEqual(parties[0][0], "democrat")
        self.assertEqual(
            {camp.id for camp in parties[0][1] if hasattr(camp, "id")},
            {self.first_campaign.id},
        )

        self.assertEqual(parties[1][0], "republican")
        self.assertEqual(
            {camp.id for camp in parties[1][1] if hasattr(camp, "id")},
            {self.second_campaign.id, self.third_campaign.id},
        )

        self.assertEqual(len(parties[0][1]), len(parties[1][1]))


class TestCampaign(DatabaseTestCase):
    """
    Test methods of the Campaign model that require database access.
    """

    def test_campaign_funds_raised(self):
        for campaign, contributions in zip(self.campaigns, self.contributions):
            self.assertEqual(
                campaign.funds_raised(), sum(cont.amount for cont in contributions)
            )

    def test_campaign_funds_raised_since_date(self):
        year = str(self.filing_period.end_date.year)
        total_funds = self.second_contribution.amount
        self.assertEqual(self.second_campaign.funds_raised(since=year), total_funds)

    def test_campaign_expenditures(self):
        for campaign, expenditures in zip(self.campaigns, self.expenditures):
            self.assertEqual(
                campaign.expenditures(), sum(exp.amount for exp in expenditures)
            )

    def test_campaign_expenditures_since_date(self):
        year = str(self.filing_period.end_date.year)
        total_expenditures = self.second_expenditure.amount
        self.assertEqual(
            self.second_campaign.expenditures(since=year), total_expenditures
        )

    def test_campaign_cash_on_hand(self):
        for campaign, filings in zip(self.campaigns, self.filings):
            filing = filings[0]
            self.assertEqual(campaign.cash_on_hand, filing.closing_balance)

    def test_campaign_share_of_funds(self):
        total = self.race.total_funds
        self.assertEqual(self.first_campaign.share_of_funds(total=total), 70)
        self.assertEqual(self.second_campaign.share_of_funds(total=total), 30)
        self.assertEqual(self.third_campaign.share_of_funds(total=total), 0)
