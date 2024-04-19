import datetime

import pytz
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase

from camp_fin.models import (
    Campaign,
    Candidate,
    County,
    District,
    Division,
    ElectionSeason,
    Entity,
    Filing,
    FilingPeriod,
    FilingType,
    Loan,
    Lobbyist,
    Office,
    OfficeType,
    PoliticalParty,
    Race,
    Status,
    Transaction,
    TransactionType,
)


class FakeTestData(object):
    """
    Mixin to set up some fake data for testing purposes.
    """

    @classmethod
    def races(cls):

        cls.first_entity = Entity.objects.create(user_id=1)
        cls.second_entity = Entity.objects.create(user_id=2)
        cls.third_entity = Entity.objects.create(user_id=3)
        cls.fourth_entity = Entity.objects.create(user_id=4)

        first_party = PoliticalParty.objects.create(name="Democrat")
        second_party = PoliticalParty.objects.create(name="Republican")
        third_party = PoliticalParty.objects.create(name="Green")

        cls.parties = (first_party, second_party, third_party)

        cls.first_candidate = Candidate.objects.create(
            first_name="first", last_name="candidate", entity=cls.first_entity
        )

        cls.second_candidate = Candidate.objects.create(
            first_name="second", last_name="candidate", entity=cls.second_entity
        )

        cls.third_candidate = Candidate.objects.create(
            first_name="third", last_name="candidate", entity=cls.third_entity
        )

        # We won't use this candidate in the Race. Create it to test filtering
        cls.non_race_candidate = Candidate.objects.create(
            first_name="non race", last_name="candidate", entity=cls.fourth_entity
        )

        status = Status.objects.create()

        cls.office_type = OfficeType.objects.create(description="test office type")

        cls.office = Office.objects.create(
            description="test office", office_type=cls.office_type, status=status
        )

        cls.district = District.objects.create(
            name="first district", office=cls.office, status=status
        )

        cls.division = Division.objects.create(
            name="first division", district=cls.district, status=status
        )

        year = datetime.datetime.now(pytz.utc).year
        last_year = year - 1
        cls.year, cls.last_year = str(year), str(last_year)

        # Generate a timestamp from two years ago for filing dates
        two_years_ago = datetime.datetime.now(pytz.utc) - datetime.timedelta(days=730)

        cls.election_season = ElectionSeason.objects.create(
            year=cls.year, special=False, status=status
        )

        cls.county = County.objects.create(name="first county")

        cls.race = Race.objects.create(
            division=cls.division,
            district=cls.district,
            office=cls.office,
            office_type=cls.office_type,
            election_season=cls.election_season,
            county=cls.county,
        )

        cls.first_campaign = Campaign.objects.create(
            candidate=cls.first_candidate,
            active_race=cls.race,
            election_season=cls.election_season,
            office=cls.office,
            date_added=datetime.datetime.now(pytz.utc),
            political_party=first_party,
        )

        cls.second_campaign = Campaign.objects.create(
            candidate=cls.second_candidate,
            active_race=cls.race,
            election_season=cls.election_season,
            office=cls.office,
            date_added=datetime.datetime.now(pytz.utc),
            political_party=second_party,
        )

        cls.third_campaign = Campaign.objects.create(
            candidate=cls.third_candidate,
            active_race=cls.race,
            election_season=cls.election_season,
            office=cls.office,
            date_added=datetime.datetime.now(pytz.utc),
            political_party=second_party,
        )

        cls.non_race_campaign = Campaign.objects.create(
            candidate=cls.non_race_candidate,
            election_season=cls.election_season,
            office=cls.office,
            date_added=datetime.datetime.now(pytz.utc),
            political_party=third_party,
        )

        cls.campaigns = [cls.first_campaign, cls.second_campaign, cls.third_campaign]

        filing_type = FilingType.objects.create(description="type")

        cls.filing_period = FilingPeriod.objects.create(
            due_date=datetime.datetime.now(pytz.utc),
            allow_no_activity=True,
            filing_period_type=filing_type,
            exclude_from_cascading=True,
            initial_date=datetime.datetime.now(pytz.utc),
            end_date=datetime.datetime.now(pytz.utc),
            email_sent_status=0,
            reminder_sent_status=0,
        )

        cls.first_filing = Filing.objects.create(
            filed_date=datetime.datetime.now(pytz.utc),
            entity=cls.first_entity,
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
            edited="0",
        )

        contribution = TransactionType.objects.create(
            description="Monetary contribution", contribution=True, anonymous=False
        )

        expenditure = TransactionType.objects.create(
            description="Monetary Expenditure", contribution=False, anonymous=False
        )

        cls.first_contribution = Transaction.objects.create(
            amount=200.0,
            received_date=datetime.datetime.now(pytz.utc),
            date_added=datetime.datetime.now(pytz.utc),
            transaction_type=contribution,
            filing=cls.first_filing,
        )

        cls.loan = Loan.objects.create(
            status=status,
            date_added=datetime.datetime.now(pytz.utc),
            received_date=datetime.datetime.now(pytz.utc),
            filing=cls.first_filing,
            amount=33.0,
        )

        cls.first_expenditure = Transaction.objects.create(
            amount=20.0,
            received_date=datetime.datetime.now(pytz.utc),
            date_added=datetime.datetime.now(pytz.utc),
            transaction_type=expenditure,
            filing=cls.first_filing,
        )

        cls.second_filing = Filing.objects.create(
            filed_date=datetime.datetime.now(pytz.utc),
            entity=cls.second_entity,
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
            edited="0",
        )

        cls.second_contribution = Transaction.objects.create(
            amount=100.0,
            received_date=datetime.datetime.now(pytz.utc),
            date_added=datetime.datetime.now(pytz.utc),
            transaction_type=contribution,
            filing=cls.second_filing,
        )

        cls.second_expenditure = Transaction.objects.create(
            amount=20.0,
            received_date=datetime.datetime.now(pytz.utc),
            date_added=datetime.datetime.now(pytz.utc),
            transaction_type=expenditure,
            filing=cls.second_filing,
        )

        cls.third_filing = Filing.objects.create(
            filed_date=datetime.datetime.now(pytz.utc),
            entity=cls.third_entity,
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
            edited="0",
        )

        cls.third_contribution = Transaction.objects.create(
            amount=0.0,
            received_date=datetime.datetime.now(pytz.utc),
            date_added=datetime.datetime.now(pytz.utc),
            transaction_type=contribution,
            filing=cls.third_filing,
        )

        cls.third_expenditure = Transaction.objects.create(
            amount=0.0,
            received_date=datetime.datetime.now(pytz.utc),
            date_added=datetime.datetime.now(pytz.utc),
            transaction_type=expenditure,
            filing=cls.third_filing,
        )

        cls.filtered_filing_period = FilingPeriod.objects.create(
            due_date=two_years_ago,
            allow_no_activity=True,
            filing_period_type=filing_type,
            exclude_from_cascading=True,
            initial_date=two_years_ago,
            end_date=two_years_ago,
            email_sent_status=0,
            reminder_sent_status=0,
        )

        cls.filtered_filing = Filing.objects.create(
            filed_date=two_years_ago,
            entity=cls.second_entity,
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
            edited="0",
        )

        cls.filtered_contribution = Transaction.objects.create(
            amount=0.0,
            received_date=two_years_ago,
            date_added=two_years_ago,
            transaction_type=contribution,
            filing=cls.filtered_filing,
        )

        cls.filtered_expenditure = Transaction.objects.create(
            amount=0.0,
            received_date=two_years_ago,
            date_added=two_years_ago,
            transaction_type=expenditure,
            filing=cls.third_filing,
        )

        cls.filings = (
            (cls.first_filing,),
            (cls.second_filing, cls.filtered_filing),
            (cls.third_filing,),
        )

        cls.contributions = (
            (cls.first_contribution, cls.loan),
            (cls.second_contribution, cls.filtered_contribution),
            (cls.third_contribution,),
        )

        cls.expenditures = (
            (cls.first_expenditure,),
            (cls.second_expenditure, cls.filtered_expenditure),
            (cls.third_expenditure,),
        )

    @classmethod
    def lobbyists(cls):
        entity_a = Entity.objects.create(user_id=1)
        entity_b = Entity.objects.create(user_id=2)

        prefix_a, first_a, last_a = "mr.", "smitty", "werben"
        first_b, mid_b, last_b, suffix_b = "jaeger", "man", "jensen", "jr."

        slug_a = "-".join((first_a, last_a, "1"))
        slug_b = "-".join((first_b, last_b, "1"))

        cls.first_lobbyist = Lobbyist(
            entity=entity_a,
            prefix=prefix_a,
            first_name=first_a,
            last_name=last_a,
            slug=slug_a,
        )

        cls.second_lobbyist = Lobbyist(
            entity=entity_b,
            first_name=first_b,
            middle_name=mid_b,
            last_name=last_b,
            suffix=suffix_b,
            slug=slug_b,
        )

        cls.first_lobbyist.save()
        cls.second_lobbyist.save()


class StatelessTestCase(TestCase, FakeTestData):
    """
        Test class that does not commit changes to the database. Inherits from TestCase so that
        every test runs in a rolled-back transaction.
    g"""

    @classmethod
    def setUpTestData(cls):
        cls.races()
        cls.lobbyists()


class DatabaseTestCase(TransactionTestCase, FakeTestData):
    """
    Test class that *does* commit changes to the database. Inherits from
    TransactionTestCase so that all changes are committed during the test,
    and rolled back via `TRUNCATE` when the test is done.
    """

    @classmethod
    def setUp(cls):
        cls.races()
        cls.lobbyists()
        call_command("aggregate_data")
