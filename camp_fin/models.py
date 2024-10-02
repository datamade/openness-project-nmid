from collections import namedtuple

from django.db import connection, models
from django.utils import timezone
from django.utils.translation import gettext as _

from camp_fin.decorators import check_date_params
from camp_fin.templatetags.helpers import format_money


class Candidate(models.Model):
    entity = models.ForeignKey("Entity", on_delete=models.CASCADE)
    prefix = models.CharField(max_length=255, null=True)
    first_name = models.CharField(max_length=255, null=True)
    middle_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    suffix = models.CharField(max_length=255, null=True)
    business_phone = models.CharField(max_length=255, null=True)
    home_phone = models.CharField(max_length=255, null=True)
    address = models.ForeignKey("Address", null=True, on_delete=models.CASCADE)
    status = models.ForeignKey("Status", null=True, on_delete=models.CASCADE)
    date_added = models.DateTimeField(null=True, default=timezone.now)
    contact = models.ForeignKey("Contact", null=True, on_delete=models.CASCADE)
    email = models.CharField(max_length=255, null=True)
    date_updated = models.DateTimeField(null=True)
    qual_candidate_id = models.IntegerField(null=True)
    deceased = models.CharField(max_length=3, null=True)

    full_name = models.CharField(max_length=500, null=True)

    slug = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.full_name or " ".join([self.first_name or "", self.last_name or ""])


class PAC(models.Model):
    entity = models.ForeignKey("Entity", on_delete=models.CASCADE)
    sos_link = models.URLField()
    name = models.CharField(max_length=100)
    acronym = models.CharField(max_length=15, null=True)
    business_phone = models.CharField(max_length=20, null=True)
    home_phone = models.CharField(max_length=20, null=True)
    email = models.CharField(max_length=255, null=True)
    address = models.ForeignKey(
        "Address",
        related_name="address",
        null=True,
        on_delete=models.CASCADE,
    )
    treasurer = models.ForeignKey("Treasurer", null=True, on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)
    status = models.ForeignKey("Status", null=True, on_delete=models.CASCADE)
    contact = models.ForeignKey("Contact", null=True, on_delete=models.CASCADE)
    date_updated = models.DateTimeField(null=True)
    bank_name = models.CharField(max_length=100, null=True)
    bank_phone = models.CharField(max_length=255, null=True)
    fax_number = models.CharField(max_length=255, null=True)
    bank_address = models.ForeignKey(
        "Address",
        related_name="pac_bank_address",
        null=True,
        on_delete=models.CASCADE,
    )
    initial_balance = models.FloatField(null=True)
    initial_balance_from_self = models.BooleanField(null=True)
    initial_debt = models.FloatField(null=True)
    initial_debt_from_self = models.BooleanField(null=True)

    slug = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.name

    @property
    def full_name(self):
        # This is here so we can treat pacs and candidates the same in
        # templates
        return self.name


class Campaign(models.Model):
    status_choices = (
        ("active", _("Active")),
        ("dropout", _("Dropped out")),
        ("lost_primary", _("Lost primary")),
    )

    olddb_id = models.IntegerField(null=True)
    candidate = models.ForeignKey("Candidate", null=True, on_delete=models.CASCADE)
    election_season = models.ForeignKey("ElectionSeason", on_delete=models.CASCADE)
    office = models.ForeignKey("Office", on_delete=models.CASCADE)
    division = models.ForeignKey("Division", null=True, on_delete=models.CASCADE)
    district = models.ForeignKey("District", null=True, on_delete=models.CASCADE)
    treasurer = models.ForeignKey("Treasurer", null=True, on_delete=models.CASCADE)
    status = models.ForeignKey("CampaignStatus", null=True, on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)
    county = models.ForeignKey("County", null=True, on_delete=models.CASCADE)
    political_party = models.ForeignKey("PoliticalParty", on_delete=models.CASCADE)
    last_updated = models.DateTimeField(null=True)
    primary_election_winner_status = models.IntegerField(null=True)
    general_election_winner_status = models.IntegerField(null=True)
    bank_name = models.CharField(max_length=100, null=True)
    bank_phone = models.CharField(max_length=255, null=True)
    bank_address = models.ForeignKey(
        "Address",
        related_name="campaign_bank_address",
        null=True,
        on_delete=models.CASCADE,
    )
    committee = models.ForeignKey(
        "PAC", related_name="campaigns", on_delete=models.CASCADE
    )

    initial_balance = models.FloatField(null=True)
    initial_balance_from_self = models.BooleanField(null=True)
    initial_debt = models.FloatField(null=True)
    initial_debt_from_self = models.BooleanField(null=True)
    qual_campaign_id = models.IntegerField(null=True)
    biannual = models.BooleanField(null=True)
    from_campaign = models.ForeignKey("Campaign", null=True, on_delete=models.CASCADE)
    active_race = models.ForeignKey("Race", null=True, on_delete=models.CASCADE)
    race_status = models.CharField(
        max_length=25, default="active", choices=status_choices, blank=True, null=True
    )
    sos_link = models.URLField()

    def __str__(self):
        office = self.office.description

        if self.candidate:
            candidate_name = "{0} {1}".format(
                self.candidate.first_name, self.candidate.last_name
            )
            return "{0} ({1})".format(candidate_name, office)
        elif self.committee.name:
            return "{0} ({1})".format(self.committee.name, office)
        else:
            party = self.political_party.name
            return "{0} ({1})".format(party, office)

    @check_date_params
    def filings(self, since=None):
        """
        Return a queryset representing all filings in a given filing period.

        Accepts an optional filter argument, `since`, as a string representing a year
        (e.g. '2017'). If `since` is present, the method will restrict contributions
        to filings starting January 1st of that year. If `since` is not specified,
        the method will return all contributions ever recorded for this campaign.
        """
        filings = self.candidate.entity.filing_set.all()

        if since:
            date = "{year}-01-01".format(year=since)
            filings = filings.filter(filed_date__gte=date)

        return filings

    @check_date_params
    def funds_raised(self, since=None):
        """
        Total funds raised in a given filing period.

        Accepts optional filter argument `since` with the same requirements as
        all other methods on this class.
        """
        # Campaigns should always have candidates, but there are occasionally
        # errors in the SOS's system. Fail gracefully by returning 0 in this
        # case, since we can't link contributions to this campaign
        if self.candidate is None:
            return 0

        entity_id = self.candidate.entity.id

        sum_contributions = """
            SELECT COALESCE(SUM(amount), 0)
            FROM contributions_by_month
            WHERE entity_id = %s
        """

        if since:
            sum_contributions += """
                AND month >= '{year}-01-01'::date
            """.format(
                year=since
            )

        cursor = connection.cursor()
        cursor.execute(sum_contributions, [entity_id])
        amount = cursor.fetchone()[0]

        return amount

    @check_date_params
    def expenditures(self, since=None):
        """
        Total expenditures in a given filing period.

        Accepts optional filter argument `since` with the same requirements as
        all other methods on this class.
        """
        entity_id = self.candidate.entity.id

        sum_expenditures = """
            SELECT COALESCE(SUM(amount), 0)
            FROM expenditures_by_month
            WHERE entity_id = %s
        """

        if since:
            sum_expenditures += """
                AND month >= '{year}-01-01'::date
            """.format(
                year=since
            )

        cursor = connection.cursor()
        cursor.execute(sum_expenditures, [entity_id])
        amount = cursor.fetchone()[0]

        return amount

    def share_of_funds(self, total=None):
        """
        This campaign's share of some portion of total funds. Defaults to the
        portion of total funds raised in this campaign's active race.
        """
        has_race = self.active_race is not None and self.active_race.total_funds > 0

        if not total:
            if has_race:
                total = self.active_race.total_funds
            else:
                return 0

        if has_race:
            percent = round(
                self.funds_raised(since=self.active_race.funding_period) / total, 2
            )

            return round(percent * 100)
        else:
            return 0

    @property
    def cash_on_hand(self):
        """
        Total amount of cash that a campaign has on hand at any given point in time.
        """
        filings = self.filing_set.order_by("-date_closed")

        on_hand = 0

        if filings:
            if (
                filings[0].filing_period.filing_period_type.description
                == "Supplemental"
            ):
                on_hand = filings[1].closing_balance + filings[0].closing_balance

            else:
                on_hand = filings[0].closing_balance

        return on_hand

    @property
    def is_winner(self):
        if getattr(self, "race", False):
            # Since the `winner` relationship is OneToOne, the ability
            # to reverse access a `race` (distinct from `active_race`)
            # means that this campaign must be the winner
            return True
        else:
            return False

    @property
    def party_identifier(self):
        """
        Return a shortened version of the Campaign's party.
        """
        if self.political_party.name:
            if "democrat" in self.political_party.name.lower():
                return "D"
            elif "republican" in self.political_party.name.lower():
                return "R"
            elif self.political_party.name.lower() == "non-partisan":
                return "NP"
            else:
                return "I"

    def get_status(self):
        """
        Return the status for this campaign.
        """
        return self.race_status

    def display_status(self):
        """
        Show a verbose version of the status for this campaign, e.g. in a template.
        """
        return dict(self.status_choices)[self.race_status]


class Race(models.Model):
    group = models.ForeignKey(
        "RaceGroup",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    office = models.ForeignKey("Office", on_delete=models.CASCADE)
    division = models.ForeignKey(
        "Division", blank=True, null=True, on_delete=models.CASCADE
    )
    district = models.ForeignKey(
        "District", blank=True, null=True, on_delete=models.CASCADE
    )
    office_type = models.ForeignKey(
        "OfficeType",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    county = models.ForeignKey(
        "County", blank=True, null=True, on_delete=models.CASCADE
    )
    election_season = models.ForeignKey("ElectionSeason", on_delete=models.CASCADE)
    winner = models.OneToOneField(
        "Campaign", blank=True, null=True, on_delete=models.CASCADE
    )
    total_contributions = models.FloatField(null=True)

    class Meta:
        unique_together = (
            "district",
            "division",
            "office_type",
            "county",
            "office",
            "election_season",
        )

    def __str__(self):
        if self.year:
            default = "{year} Race for {office}".format(
                year=self.year, office=self.office
            )
            specific = "%s Race for {specifier} {office}" % str(self.year)
        else:
            default = "Race for {office}".format(office=self.office)
            specific = "Race for {specifier} {office}"

        if self.office_type:
            if self.office_type.description in ("Statewide", "Judicial"):
                return default

            elif (
                self.office_type.description
                in ("Legislative", "Public Regulation Commission")
                and self.district is not None
            ):
                return specific.format(specifier=self.district, office=self.office)

            elif (
                self.office_type.description == "County Offices"
                and self.county is not None
            ):
                return specific.format(specifier=self.county, office=self.office)

            else:
                return default
        else:
            return default

    @property
    def campaigns(self):
        """
        Return all campaigns involved in this race.
        """
        return self.campaign_set.all()

    @property
    def sorted_campaigns(self):
        """
        Return all campaigns involved in this race, in reverse order of how much
        money they've raised.
        """
        return sorted(
            [camp for camp in self.campaigns],
            key=lambda camp: camp.funds_raised(since=self.funding_period),
            reverse=True,
        )

    @property
    def active_campaigns(self):
        """
        Campaigns that are still active in this race.
        """
        return sorted(
            [camp for camp in self.campaigns if camp.get_status() == "active"],
            key=lambda camp: camp.funds_raised(since=self.funding_period),
            reverse=True,
        )

    @property
    def sorted_dropouts(self):
        """
        Campaigns that have dropped out of this race, sorted by funds raised.
        """
        return sorted(
            [camp for camp in self.campaigns if camp.get_status() != "active"],
            key=lambda camp: camp.funds_raised(since=self.funding_period),
            reverse=True,
        )

    @property
    def num_candidates(self):
        """
        Return the number of candidates involved in this race.
        """
        return self.campaigns.count()

    @property
    def largest_contribution(self):
        """
        Return the amount of funds raised for the largest campaign in this race.
        """
        if self.num_candidates > 0:
            return self.sorted_campaigns[0].funds_raised(since=self.funding_period)
        else:
            return 0

    @property
    def year(self):
        """
        If this race has an ElectionSeason, return the year of the race.
        Otherwise, return None.
        """
        return getattr(self.election_season, "year", None)

    @property
    def funding_period(self):
        """
        If this race has an ElectionSeason, return the year that the funding
        period started. Otherwise, return None.
        """
        if self.year:
            return str(int(self.year) - 1)
        else:
            return None

    def sum_campaign_contributions(self):
        """
        Get the sum of contributions from campaigns in this race.
        """
        return sum(
            campaign.funds_raised(since=self.funding_period)
            for campaign in self.campaigns
        )

    @property
    def total_funds(self):
        """
        Return the total amount of money raised in this race, aggreggated from
        the total contributions to each campaign during the election season.
        """
        # Default to the attribute that should be aggregated during the `make_races`
        # management command
        if self.total_contributions is not None:
            return self.total_contributions
        else:
            # Fallback
            return self.sum_campaign_contributions()

    @property
    def campaigns_by_party(self):
        """
        Return a list of campaigns in this race, organized by party.
        """
        campaigns = [
            ("democrat", self.campaign_set.filter(political_party__name="Democrat")),
            (
                "republican",
                self.campaign_set.filter(political_party__name="Republican"),
            ),
            (
                "other",
                self.campaign_set.exclude(
                    political_party__name__in=["Democrat", "Republican"]
                ),
            ),
        ]

        biggest_party = max(queryset.count() for party, queryset in campaigns)

        campaign_list = []
        for party, queryset in campaigns:
            if queryset.count() > 0:
                # Sort campaigns by funds raised
                formatted_campaigns = sorted(
                    [campaign for campaign in queryset],
                    key=lambda camp: camp.funds_raised(since=self.year),
                    reverse=True,
                )
                if queryset.count() < biggest_party:
                    # Add empty campaigns so that the table rows will line up
                    formatted_campaigns += [
                        {} for missing in range(biggest_party - queryset.count())
                    ]

                campaign_list.append((party, formatted_campaigns))

        return campaign_list


class RaceGroup(models.Model):
    short_title = models.CharField(max_length=50)
    full_title = models.CharField(max_length=50)
    description = models.CharField(max_length=250)

    def __str__(self):
        return self.full_title


class OfficeType(models.Model):
    description = models.CharField(max_length=50)

    def __str__(self):
        return self.description


class Office(models.Model):
    description = models.CharField(max_length=100)
    status = models.ForeignKey("Status", db_constraint=False, on_delete=models.CASCADE)
    office_type = models.ForeignKey("OfficeType", null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.description


class District(models.Model):
    office = models.ForeignKey("Office", on_delete=models.CASCADE)
    name = models.CharField(max_length=256)
    status = models.ForeignKey("Status", db_constraint=False, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class County(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class PoliticalParty(models.Model):
    name = models.CharField(max_length=256)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    contact = models.ForeignKey("Contact", null=True, on_delete=models.CASCADE)
    amount = models.FloatField(db_index=True)
    received_date = models.DateTimeField(db_index=True)
    date_added = models.DateTimeField(default=timezone.now)
    check_number = models.CharField(max_length=100, null=True)
    memo = models.TextField(null=True)
    description = models.CharField(max_length=75, null=True)
    transaction_type = models.ForeignKey("TransactionType", on_delete=models.CASCADE)
    filing = models.ForeignKey("Filing", on_delete=models.CASCADE)
    olddb_id = models.IntegerField(null=True)
    name_prefix = models.CharField(max_length=25, null=True)
    first_name = models.CharField(max_length=255, null=True)
    middle_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    suffix = models.CharField(max_length=15, null=True)
    company_name = models.CharField(max_length=255, null=True, db_index=True)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=25, null=True)
    zipcode = models.CharField(max_length=255, null=True)
    county = models.ForeignKey("County", null=True, on_delete=models.CASCADE)
    country = models.CharField(max_length=100, null=True)
    contact_type = models.ForeignKey("ContactType", null=True, on_delete=models.CASCADE)
    transaction_status = models.ForeignKey(
        "Status", db_constraint=False, null=True, on_delete=models.CASCADE
    )
    from_file_id = models.IntegerField(null=True)
    contact_type_other = models.CharField(max_length=25, null=True)
    occupation = models.CharField(max_length=255, null=True)
    expenditure_for_certified_candidate = models.BooleanField(null=True)

    full_name = models.CharField(max_length=500, null=True)

    redact = models.BooleanField(default=False, null=True)

    def __str__(self):
        if self.redact:
            return "Redacted by donor request"

        return self.full_name or self.company_name

    @property
    def transaction_subject(self):
        # This is here so that the API key makes a little more sense
        return self.filing

    @property
    def full_address(self):
        if self.redact:
            return "Redacted by donor request"

        full_address = ""

        if self.address:
            full_address = "{}".format(self.address)

        if self.city:
            full_address = "{0} {1}".format(full_address, self.city)

        if self.state:
            full_address = "{0}, {1}".format(full_address, self.state)

        if self.zipcode:
            full_address = "{0} {1}".format(full_address, self.zipcode)

        return full_address.strip()


class TransactionType(models.Model):
    description = models.CharField(max_length=50)
    contribution = models.BooleanField()
    anonymous = models.BooleanField()

    def __str__(self):
        return self.description


class Loan(models.Model):
    contact = models.ForeignKey("Contact", null=True, on_delete=models.CASCADE)
    status = models.ForeignKey("Status", db_constraint=False, on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)
    amount = models.FloatField()
    check_number = models.CharField(max_length=30, null=True)
    memo = models.CharField(max_length=500, null=True)
    received_date = models.DateTimeField()
    interest_rate = models.FloatField(null=True)
    due_date = models.DateTimeField(null=True)
    payment_schedule_id = models.IntegerField(null=True)
    filing = models.ForeignKey("Filing", null=True, on_delete=models.CASCADE)
    olddb_id = models.IntegerField(null=True)
    name_prefix = models.CharField(max_length=25, null=True)
    first_name = models.CharField(max_length=255, null=True)
    middle_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    suffix = models.CharField(max_length=15, null=True)
    company_name = models.CharField(max_length=255, null=True)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=255, null=True)
    state = models.CharField(max_length=25, null=True)
    zipcode = models.CharField(max_length=255, null=True)
    county = models.ForeignKey("County", null=True, on_delete=models.CASCADE)
    country = models.CharField(max_length=255, null=True)
    contact_type = models.ForeignKey("ContactType", null=True, on_delete=models.CASCADE)
    from_file_id = models.IntegerField(null=True)
    contact_type_other = models.CharField(max_length=25, null=True)
    occupation = models.CharField(max_length=255, null=True)
    loan_transfer_date = models.DateTimeField(null=True)
    from_file_id = models.IntegerField(null=True)

    full_name = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.full_name

    @property
    def full_address(self):
        full_address = ""

        if self.address:
            full_address = "{}".format(self.address)

        if self.city:
            full_address = "{0} {1}".format(full_address, self.city)

        if self.state:
            full_address = "{0}, {1}".format(full_address, self.state)

        if self.zipcode:
            full_address = "{0} {1}".format(full_address, self.zipcode)

        if self.country:
            full_address = "{0} {1}".format(full_address, self.country)

        return full_address.strip()


class LoanTransaction(models.Model):
    loan = models.ForeignKey("Loan", on_delete=models.CASCADE)
    amount = models.FloatField()
    interest_paid = models.FloatField(null=True)
    transaction_date = models.DateTimeField()
    date_added = models.DateTimeField(default=timezone.now)
    check_number = models.CharField(max_length=255, null=True)
    memo = models.TextField(null=True)
    transaction_type = models.ForeignKey(
        "LoanTransactionType", on_delete=models.CASCADE
    )
    transaction_status = models.ForeignKey(
        "Status", db_constraint=False, on_delete=models.CASCADE
    )
    filing = models.ForeignKey("Filing", on_delete=models.CASCADE)
    from_file_id = models.IntegerField(null=True)

    def __str__(self):
        return "{0} {1}".format(self.transaction_type, format_money(self.amount))


class LoanTransactionType(models.Model):
    description = models.CharField(max_length=25)

    def __str__(self):
        return self.description


class SpecialEvent(models.Model):
    event_name = models.CharField(max_length=255, null=True)
    transaction_status = models.ForeignKey(
        "Status", db_constraint=False, on_delete=models.CASCADE
    )
    date_added = models.DateTimeField(default=timezone.now)
    event_date = models.DateField()
    admission_price = models.FloatField()
    attendance = models.IntegerField()
    location = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True)
    sponsors = models.TextField(null=True)
    total_admissions = models.FloatField()
    anonymous_contributions = models.FloatField()
    total_expenditures = models.FloatField()
    filing = models.ForeignKey("Filing", on_delete=models.CASCADE)
    olddb_id = models.IntegerField(null=True)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100, null=True)
    zipcode = models.CharField(max_length=255, null=True)
    county = models.ForeignKey("County", null=True, on_delete=models.CASCADE)
    country = models.CharField(max_length=255, null=True)
    from_file_id = models.IntegerField(null=True)

    def __str__(self):
        if self.event_name:
            return self.event_name
        else:
            return "Event sponsored by {0} on {1}".format(
                self.sponsors, self.event_date
            )


class Filing(models.Model):
    entity = models.ForeignKey("Entity", on_delete=models.CASCADE)
    olddb_campaign_id = models.IntegerField(null=True)
    olddb_profile_id = models.IntegerField(null=True)
    report_id = models.IntegerField(null=True)
    report_version_id = models.IntegerField(null=True)
    filing_period = models.ForeignKey("FilingPeriod", on_delete=models.CASCADE)
    status = models.ForeignKey("Status", null=True, on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)
    olddb_ethics_report_id = models.IntegerField(null=True)
    campaign = models.ForeignKey("Campaign", null=True, on_delete=models.CASCADE)
    filed_date = models.DateTimeField()
    date_closed = models.DateTimeField(null=True)
    date_last_amended = models.DateTimeField(null=True)
    opening_balance = models.FloatField(null=True)
    total_contributions = models.FloatField(null=True)
    total_expenditures = models.FloatField(null=True)
    total_loans = models.FloatField(null=True)
    total_inkind = models.FloatField(null=True)
    total_unpaid_debts = models.FloatField(null=True)
    closing_balance = models.FloatField(null=True)
    total_debt_carried_forward = models.FloatField(null=True)
    total_debt_paid = models.FloatField(null=True)
    total_loans_forgiven = models.FloatField(null=True)
    pdf_report = models.CharField(max_length=1000, null=True)
    final = models.BooleanField(null=True)
    no_activity = models.BooleanField(null=True)
    supplement_count = models.IntegerField(null=True)
    total_supplemental_contributions = models.FloatField(null=True)
    edited = models.CharField(max_length=3, null=True)
    regenerate = models.CharField(max_length=3, null=True)

    def __str__(self):
        if self.campaign and self.campaign.candidate:
            return "{0} {1} {2}".format(
                self.campaign.candidate.first_name,
                self.campaign.candidate.last_name,
                self.filing_period,
            )
        else:
            if self.entity.pac_set.first():
                return self.entity.pac_set.first().name
            return str(self.entity)

    @check_date_params
    def contributions(self, since=None):
        """
        Return the contributions (as Transaction objects) represented by this filing,
        filtered by an optional year (the `since` parameter).

        We need this method because filing periods can span multiple years, so
        the `total_contributions` can't reliably disaggregate contributions that
        occurred in one year but were reported in the next.
        """
        contributions = self.transaction_set.filter(transaction_type__contribution=True)

        if since:
            date = "{year}-01-01".format(year=since)
            contributions = contributions.filter(received_date__gte=date)

        return contributions

    @check_date_params
    def loans(self, since=None):
        """
        Return the loans (as LoanTransaction objects) represented by this filing.
        Same params and reasoning as the `contributions` method.
        """
        desc = "Payment"
        loans = self.loantransaction_set.filter(transaction_type__description=desc)

        if since:
            date = "{year}-01-01".format(year=since)
            loans = loans.filter(transaction_date__gte=date)

        return loans

    @check_date_params
    def expenditures(self, since=None):
        """
        Return the expenditures (as Transaction objects) represented by this filing.
        Same params and reasoning as the `contributions` method.
        """
        desc = "Monetary Expenditure"
        expenditures = self.transaction_set.filter(transaction_type__description=desc)

        if since:
            date = "{year}-01-01".format(year=since)
            expenditures = expenditures.filter(received_date__gte=date)

        return expenditures


class FilingPeriod(models.Model):
    due_date = models.DateTimeField()
    olddb_id = models.IntegerField(null=True)
    description = models.CharField(max_length=255, null=True)
    allow_no_activity = models.BooleanField()
    filing_period_type = models.ForeignKey("FilingType", on_delete=models.CASCADE)
    exclude_from_cascading = models.BooleanField()
    supplemental_init_date = models.DateTimeField(null=True)
    regular_filing_period = models.ForeignKey(
        "RegularFilingPeriod", null=True, on_delete=models.CASCADE
    )
    initial_date = models.DateField()
    end_date = models.DateField()
    email_sent_status = models.IntegerField()
    reminder_sent_status = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return "{0}/{1} ({2})".format(
            self.initial_date.month,
            self.initial_date.year,
            self.filing_period_type.description,
        )


class Address(models.Model):
    street = models.CharField(null=True, max_length=255)
    city = models.CharField(null=True, max_length=255)
    state = models.ForeignKey("State", null=True, on_delete=models.CASCADE)
    zipcode = models.CharField(null=True, max_length=100)
    county = models.ForeignKey("County", null=True, on_delete=models.CASCADE)
    country = models.CharField(max_length=255, null=True)
    address_type = models.ForeignKey("AddressType", null=True, on_delete=models.CASCADE)
    olddb_id = models.IntegerField(null=True)
    date_added = models.DateTimeField(null=True, default=timezone.now)
    from_file_id = models.IntegerField(null=True)

    def __str__(self):
        if self.street:
            street = self.street.strip()
            city = self.city.strip()
            state = str(self.state).strip()
            zipcode = self.zipcode.strip()

            address = "{0} {1}, {2} {3}".format(street, city, state, zipcode)
        else:
            address = "No address found"

        return address


class CampaignStatus(models.Model):
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.description


class Division(models.Model):
    name = models.CharField(max_length=25)
    district = models.ForeignKey("District", on_delete=models.CASCADE)
    status = models.ForeignKey("Status", on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class ElectionSeason(models.Model):
    year = models.CharField(max_length=5)
    special = models.BooleanField()
    status = models.ForeignKey("Status", db_constraint=False, on_delete=models.CASCADE)

    def __str__(self):
        return "Election year {}".format(self.year)


class Entity(models.Model):
    user_id = models.IntegerField(null=True)
    entity_type = models.ForeignKey("EntityType", null=True, on_delete=models.CASCADE)
    olddb_id = models.IntegerField(null=True)

    def __str__(self):
        return "Entity {}".format(self.entity_type)

    @check_date_params
    def trends(self, since="2010"):
        """
        Generate a dict of filing trends for use in contribution/expenditure charts
        for this Entity.
        """
        # Balances and debts
        summed_filings = """
            SELECT
              SUM(COALESCE(f.total_unpaid_debts, 0)) AS total_unpaid_debts,
              SUM(f.closing_balance) AS closing_balance,
              f.filed_date
            FROM camp_fin_filing AS f
            JOIN camp_fin_filingperiod AS fp
              ON f.filing_period_id = fp.id
            WHERE f.entity_id = %s
              AND fp.exclude_from_cascading = FALSE
              AND fp.regular_filing_period_id IS NULL
              AND f.filed_date >= '{year}-01-01'
            GROUP BY f.filed_date
            ORDER BY f.filed_date
        """.format(
            year=since
        )

        cursor = connection.cursor()

        cursor.execute(summed_filings, [self.id])

        balance_trend, debt_trend = [], []

        for (
            total_unpaid_debts,
            closing_balance,
            filed_date,
        ) in cursor:
            filing_date = (filed_date.year, filed_date.month, filed_date.day)
            balance_trend.append([closing_balance, *filing_date])
            debt_trend.append([total_unpaid_debts * -1, *filing_date])

        output_trends = {"balance_trend": balance_trend, "debt_trend": debt_trend}

        # Donations and expenditures
        monthly_query = """
            SELECT
              months.year,
              months.month,
              COALESCE({table}.amount, 0) AS amount
            FROM (
              SELECT
                DISTINCT DATE_PART('year', month) AS year,
                GENERATE_SERIES(1, 12) AS month
              FROM {table}_by_month
              ORDER BY year, month
            ) months
            JOIN (
              SELECT
                {table}.amount AS amount,
                DATE_PART('month', {table}.month) AS month,
                DATE_PART('year', {table}.month) AS year
              FROM {table}_by_month AS {table}
              WHERE {table}.entity_id = %s
                AND {table}.month >= '{year}-01-01'::date
            ) {table}
            USING (year, month)
            ORDER BY year, month
        """

        contributions_query = monthly_query.format(table="contributions", year=since)

        cursor.execute(contributions_query, [self.id])

        donation_trend = [[amount, year, month, 1] for year, month, amount in cursor]

        expenditures_query = monthly_query.format(table="expenditures", year=since)

        cursor.execute(expenditures_query, [self.id])

        expend_trend = [[amount * -1, year, month, 1] for year, month, amount in cursor]

        output_trends["donation_trend"] = donation_trend
        output_trends["expend_trend"] = expend_trend

        return output_trends


class EntityType(models.Model):
    description = models.CharField(max_length=256)

    def __str__(self):
        return self.description


class FilingType(models.Model):
    description = models.CharField(max_length=25)

    def __str__(self):
        return self.description


class Treasurer(models.Model):
    prefix = models.CharField(max_length=255, null=True)
    first_name = models.CharField(max_length=255, null=True)
    middle_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    suffix = models.CharField(max_length=255, null=True)
    business_phone = models.CharField(max_length=255, null=True)
    alt_phone = models.CharField(max_length=255, null=True)
    email = models.CharField(max_length=255, null=True)
    address = models.ForeignKey("Address", on_delete=models.CASCADE)
    date_added = models.DateTimeField(default=timezone.now)
    status = models.ForeignKey("Status", on_delete=models.CASCADE)
    olddb_entity_id = models.IntegerField(null=True)

    full_name = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.full_name


class Contact(models.Model):
    prefix = models.CharField(max_length=255, null=True)
    first_name = models.CharField(max_length=255, null=True)
    middle_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    suffix = models.CharField(max_length=255, null=True)
    occupation = models.CharField(max_length=100, null=True)
    address = models.ForeignKey("Address", on_delete=models.CASCADE)
    phone = models.CharField(max_length=30, null=True)
    email = models.CharField(max_length=100, null=True)
    memo = models.TextField(null=True)
    company_name = models.CharField(max_length=255, null=True)
    contact_type = models.ForeignKey("ContactType", on_delete=models.CASCADE)
    status = models.ForeignKey("Status", db_constraint=False, on_delete=models.CASCADE)
    olddb_id = models.IntegerField(null=True)
    date_added = models.DateTimeField(null=True, default=timezone.now)
    entity = models.ForeignKey("Entity", on_delete=models.CASCADE)
    from_file_id = models.IntegerField(null=True)

    full_name = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.full_name


class ContactType(models.Model):
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.description


class State(models.Model):
    postal_code = models.CharField(max_length=2, null=True)

    def __str__(self):
        if self.postal_code:
            return self.postal_code
        return ""


class Story(models.Model):
    """
    NMID stories that accompany candidates, campaigns, and races.
    """

    class Meta:
        verbose_name_plural = "stories"

    link = models.URLField()
    title = models.CharField(max_length=500)
    candidate = models.ManyToManyField("Candidate", blank=True)
    race = models.ManyToManyField("Race", blank=True)


class LobbyistMethodMixin(object):
    """
    Mixin class to provide some base methods for Lobbyists and Organizations
    (lobbyist employers).
    """

    def get_employments(self, reverse_attr="organization"):
        """
        Method for traversing employments and returning either
            - Lobbyists employed by this entity
            - Organizations that have employed this entity
        """
        # Enforce params
        assert reverse_attr in ["organization", "lobbyist"]

        # Since each year that a lobbyist registers with an employer counts as
        # a separate employment, iterate the list and group together employers
        sorted_employments = []
        employment_cache = {}
        for employment in self.lobbyistemployer_set.order_by("-year"):
            entity_id = getattr(getattr(employment, reverse_attr), "id")
            year = employment.year

            if entity_id in employment_cache.keys():
                # Org entry exists; append this year to its list of active years
                employment_cache[entity_id]["years"].append(year)
            else:
                # Create a new entry and initialize the list of active years
                details = {
                    reverse_attr: getattr(employment, reverse_attr),
                    "years": [year],
                }
                employment_cache[entity_id] = details

                # Keep track of the order of this organization
                sorted_employments.append(entity_id)

        return [employment_cache[entity] for entity in sorted_employments]

    def total_contributions(self, employer_id=None):
        """
        Return the total amount of money that this entity has contributed
        to political campaigns.
        """
        entity_id = self.entity.id

        sum_contributions = """
            SELECT SUM(COALESCE(political_contributions, 0))
            FROM camp_fin_lobbyistreport
            WHERE entity_id = %s
        """

        with connection.cursor() as cursor:
            cursor.execute(sum_contributions, [entity_id])
            amount = cursor.fetchone()[0]

        return amount

    def total_expenditures(self, employer_id=None):
        """
        Return the total amount of money that this entity has spent on lobbying,
        for any purpose.
        """
        entity_id = self.entity.id

        sum_contributions = """
            SELECT SUM(COALESCE(expenditures, 0))
            FROM camp_fin_lobbyistreport
            WHERE entity_id = %s
        """

        with connection.cursor() as cursor:
            cursor.execute(sum_contributions, [entity_id])
            amount = cursor.fetchone()[0]

        return amount

    @property
    def years_active(self):
        """
        The range of time that this entity has been employed.
        """
        years = self.lobbyistemployer_set.aggregate(
            min_year=models.Min("year"), max_year=models.Max("year")
        )

        if years.get("min_year") and years.get("max_year"):
            min_year, max_year = years["min_year"], years["max_year"]
            if min_year == max_year:
                # Only active for one year
                return [min_year]
            else:
                return [year for year in range(int(min_year), int(max_year) + 1)]
        else:
            return []

    def transaction_query(
        self,
        order_by="amount",
        ordering="desc",
        ttype="contribution",
        bulk=False,
        start_date=None,
        end_date=None,
    ):
        """
        Return a query we can use to get transactions (contributions and expenditures)
        for this entity.
        """
        # Check params for validity
        assert order_by in [
            "recipient",
            "amount",
            "description",
            "beneficiary",
            "expenditure_purpose",
            "received_date",
        ]
        assert ordering in ["asc", "desc"]
        assert ttype in ["contribution", "expenditure"]
        assert bulk in [True, False]  # Whether or not this is a bulk download

        get_transactions = """
            SELECT
              trans.id AS transaction_id,
              report.entity_id AS entity_id,
              {select_name} AS name,
              COALESCE(trans.name, '') AS recipient,
              trans.amount,
              COALESCE(trans.beneficiary, '') AS beneficiary,
              COALESCE(ttype.description, '') AS type,
              COALESCE(trans.expenditure_purpose, '') AS description,
              trans.received_date AS date
            FROM camp_fin_lobbyistreport report
            {join_name}
            JOIN camp_fin_lobbyisttransaction trans
              ON trans.lobbyist_report_id = report.id
            JOIN camp_fin_lobbyisttransactiontype ttype
              ON trans.lobbyist_transaction_type_id = ttype.id
        """

        # Name will differ depending on the entity type --
        # children will need to implement the select_name and join_name attributes
        get_transactions = get_transactions.format(
            select_name=self.select_name, join_name=self.join_name
        )

        if not bulk:
            get_transactions += """
                WHERE entity_id = %s
            """

        if ttype == "contribution":
            # Although we don't have access to that table, you can tell that
            # transactions with the ID 2 are political contributions
            get_transactions += """
                AND ttype.group_id = 2
            """
        else:
            get_transactions += """
                AND ttype.group_id = 1
            """

        # Optional params for external querying methods
        if start_date:
            get_transactions += """
                AND trans.received_date >= %s
            """

        if end_date:
            get_transactions += """
                AND trans.received_date <= %s
            """

        get_transactions += """
            ORDER BY {0} {1}
        """.format(
            order_by, ordering
        )

        return get_transactions

    def get_transactions(
        self, order_by="amount", ordering="desc", ttype="contribution", bulk=False
    ):
        """
        use `transaction_query` to generate a list of transactions (contributions
        and expenditures) for this entity.
        """
        query = self.transaction_query(order_by, ordering, ttype, bulk)

        with connection.cursor() as cursor:
            if bulk:
                # Bulk download -- don't specify entity ID
                cursor.execute(query)
            else:
                cursor.execute(query, [self.entity_id])

            columns = [c[0] for c in cursor.description]
            trans_tuple = namedtuple("Transaction", columns)

            output = [trans_tuple(*r) for r in cursor]

        return output

    def contributions(self, order_by="amount", ordering="desc"):
        """
        Return a list of all political contributions from this entity.
        """
        return self.get_transactions(order_by, ordering, ttype="contribution")

    def expenditures(self, order_by="amount", ordering="desc"):
        """
        Return a list of all expenditures from this entity.
        """
        return self.get_transactions(order_by, ordering, ttype="expenditure")

    @classmethod
    def top(cls, order_by="rank", sort_order="asc", limit=""):
        """
        Return the top entities in this class, ordered by the `order_by` param and sorted
        by the `sort_order` param.
        """
        clsname = cls.__name__
        etype = clsname.lower()

        entity_query = """
            SELECT * FROM (
                SELECT
                    DENSE_RANK() OVER (
                        ORDER BY {etype}s.contributions + {etype}s.expenditures DESC
                    ) AS rank,
                    {etype}s.*
                FROM (
                    SELECT DISTINCT ON ({etype}.id)
                        {etype}.id,
                        SUM(COALESCE(report.political_contributions, 0)) AS contributions,
                        SUM(COALESCE(report.expenditures, 0)) AS expenditures
                    FROM camp_fin_{etype} AS {etype}
                    JOIN camp_fin_lobbyistreport AS report
                    USING(entity_id)
                    GROUP BY {etype}.id
                ) AS {etype}s
            ) AS s
            ORDER BY {order_by} {sort_order}
        """.format(
            etype=etype, order_by=order_by, sort_order=sort_order
        )

        if limit:
            entity_query += """
                LIMIT {limit}
            """.format(
                limit=limit
            )

        with connection.cursor() as cursor:
            cursor.execute(entity_query)

            columns = [c[0] for c in cursor.description]
            entity_tuple = namedtuple(clsname, columns)

            entities = [entity_tuple(*r) for r in cursor]

        queryset = [(entity.rank, cls.objects.get(id=entity.id)) for entity in entities]

        return queryset


class Lobbyist(models.Model, LobbyistMethodMixin):
    entity = models.ForeignKey("Entity", on_delete=models.CASCADE)
    status = models.ForeignKey("Status", null=True, on_delete=models.CASCADE)
    date_added = models.DateTimeField(null=True, default=timezone.now)
    prefix = models.CharField(max_length=255, null=True)
    first_name = models.CharField(max_length=255, null=True)
    middle_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    suffix = models.CharField(max_length=255, null=True)
    email = models.CharField(max_length=100, null=True)
    registration_date = models.DateTimeField(null=True)
    termination_date = models.DateTimeField(null=True)
    filing_period = models.ForeignKey(
        "LobbyistFilingPeriod", null=True, on_delete=models.CASCADE
    )
    permanent_address = models.ForeignKey(
        "Address",
        related_name="lobbyist_permanent_address",
        null=True,
        on_delete=models.CASCADE,
    )
    lobbying_address = models.ForeignKey(
        "Address",
        related_name="lobbyist_lobbying_address",
        null=True,
        on_delete=models.CASCADE,
    )
    contact = models.ForeignKey("Contact", null=True, on_delete=models.CASCADE)
    phone = models.CharField(max_length=30, null=True)
    date_updated = models.DateTimeField(null=True)
    slug = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        """
        Return the full name of this lobbyist.
        """
        name_parts = [
            self.prefix,
            self.first_name,
            self.middle_name,
            self.last_name,
            self.suffix,
        ]

        return " ".join(name.strip() for name in name_parts if name is not None)

    @property
    def employers(self):
        """
        Return a list of Organizations that have employed this Lobbyist in the
        form of LobbyistEmployer objects, in descending order of how recent the
        term of employment was.
        """
        return self.get_employments(reverse_attr="organization")

    @property
    def select_name(self):
        """
        Return valid SQL for selecting this lobbyist's name. Used in the `transaction_query`
        method.
        """
        return """
            CONCAT_WS(' ', lobbyist.prefix,
                           lobbyist.first_name,
                           lobbyist.middle_name,
                           lobbyist.last_name,
                           lobbyist.suffix)
        """

    @property
    def join_name(self):
        """
        Return valid SQL for joining this lobbyist's table to the lobbyist reports. Used in the
        `transaction_query` method.
        """
        return """
            JOIN camp_fin_lobbyist AS lobbyist
                USING(entity_id)
        """


class Organization(models.Model, LobbyistMethodMixin):
    entity = models.ForeignKey("Entity", on_delete=models.CASCADE)
    date_added = models.DateTimeField(null=True, default=timezone.now)
    status = models.ForeignKey("Status", null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100, null=True)
    permanent_address = models.ForeignKey(
        "Address",
        related_name="organization_permanent_address",
        null=True,
        on_delete=models.CASCADE,
    )
    contact = models.ForeignKey("Contact", on_delete=models.CASCADE)
    date_updated = models.DateTimeField(null=True)
    phone = models.CharField(max_length=30, null=True)
    slug = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.name

    @property
    def lobbyists(self):
        """
        Return a list of Organizations that have employed this Lobbyist in the
        form of LobbyistEmployer objects, in descending order of how recent the
        term of employment was.
        """
        return self.get_employments(reverse_attr="lobbyist")

    @property
    def select_name(self):
        """
        Return valid SQL for selecting this organization's name. Used in the `transaction_query`
        method.
        """
        return """
            organization.name
        """

    @property
    def join_name(self):
        """
        Return valid SQL for joining this organization's table to the lobbyist reports. Used in the
        `transaction_query` method.
        """
        return """
            JOIN camp_fin_organization AS organization
                USING(entity_id)
        """


class LobbyistRegistration(models.Model):
    lobbyist = models.ForeignKey("Lobbyist", on_delete=models.CASCADE)
    date_added = models.DateTimeField(null=True, default=timezone.now)
    year = models.CharField(max_length=5)
    is_registered = models.BooleanField(null=True)


class LobbyistEmployer(models.Model):
    lobbyist = models.ForeignKey("Lobbyist", on_delete=models.CASCADE)
    organization = models.ForeignKey("Organization", on_delete=models.CASCADE)
    date_added = models.DateTimeField(null=True, default=timezone.now)
    year = models.CharField(max_length=5)


class LobbyistFilingPeriod(models.Model):
    filing_date = models.DateTimeField(null=True)
    due_date = models.DateTimeField(null=True)
    description = models.CharField(max_length=100)
    allow_statement_of_no_activity = models.BooleanField(null=True)
    initial_date = models.DateTimeField(null=True)
    lobbyist_filing_period_type = models.ForeignKey(
        "LobbyistFilingPeriodType",
        null=True,
        on_delete=models.CASCADE,
    )
    regular_filing_period = models.ForeignKey(
        "FilingPeriod", null=True, on_delete=models.CASCADE
    )


class LobbyistTransaction(models.Model):
    lobbyist_report = models.ForeignKey(
        "LobbyistReport", null=True, on_delete=models.CASCADE
    )
    name = models.CharField(max_length=250, null=True)
    beneficiary = models.CharField(max_length=250, null=True)
    expenditure_purpose = models.CharField(max_length=250, null=True)
    lobbyist_transaction_type = models.ForeignKey(
        "LobbyistTransactionType",
        null=True,
        on_delete=models.CASCADE,
    )
    received_date = models.DateTimeField(null=True)
    amount = models.FloatField()
    date_added = models.DateTimeField(null=True, default=timezone.now)
    transaction_status = models.ForeignKey(
        "LobbyistTransactionStatus",
        null=True,
        on_delete=models.CASCADE,
    )


class LobbyistTransactionType(models.Model):
    description = models.CharField(max_length=100)
    group = models.ForeignKey(
        "LobbyistTransactionGroup",
        null=True,
        on_delete=models.CASCADE,
    )


class LobbyistReport(models.Model):
    entity = models.ForeignKey("Entity", on_delete=models.CASCADE)
    lobbyist_filing_period = models.ForeignKey(
        "LobbyistFilingPeriod", null=True, on_delete=models.CASCADE
    )
    status = models.ForeignKey("Status", null=True, on_delete=models.CASCADE)
    date_added = models.DateTimeField(null=True, default=timezone.now)
    date_closed = models.DateTimeField(null=True)
    date_updated = models.DateTimeField(null=True)
    pdf_report = models.CharField(max_length=255, null=True)
    meal_beverage_expenses = models.FloatField(null=True)
    entertainment_expenses = models.FloatField(null=True)
    gift_expenses = models.FloatField(null=True)
    other_expenses = models.FloatField(null=True)
    special_event_expenses = models.FloatField(null=True)
    expenditures = models.FloatField(null=True)
    political_contributions = models.FloatField(null=True)


class LobbyistSpecialEvent(models.Model):
    lobbyist_report = models.ForeignKey("LobbyistReport", on_delete=models.CASCADE)
    event_type = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    received_date = models.DateTimeField(null=True)
    amount = models.FloatField()
    groups_invited = models.CharField(max_length=2000, null=True)
    date_added = models.DateTimeField(null=True, default=timezone.now)
    transaction_status = models.ForeignKey(
        "LobbyistTransactionStatus",
        null=True,
        on_delete=models.CASCADE,
    )


class LobbyistBundlingDisclosure(models.Model):
    destinatary_name = models.CharField(max_length=100)
    lobbyist_report = models.ForeignKey("LobbyistReport", on_delete=models.CASCADE)
    date_added = models.DateTimeField(null=True, default=timezone.now)
    transaction_status = models.ForeignKey(
        "LobbyistTransactionStatus",
        null=True,
        on_delete=models.CASCADE,
    )


class LobbyistBundlingDisclosureContributor(models.Model):
    bundling_disclosure = models.ForeignKey(
        "LobbyistBundlingDisclosure",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=100)
    address = models.ForeignKey(
        "Address",
        related_name="lobbyist_bundling_disclosure_contributor_address",
        null=True,
        on_delete=models.CASCADE,
    )
    amount = models.FloatField()
    occupation = models.CharField(max_length=250, null=True)
    lobbyist_report = models.ForeignKey(
        "LobbyistReport", null=True, on_delete=models.CASCADE
    )


##################################################################
# Below here are normalized tables that we may or may not end up #
# getting. Just stubbing them out in case we do                  #
##################################################################


class RegularFilingPeriod(models.Model):
    pass


class Status(models.Model):
    pass


class AddressType(models.Model):
    pass


class LobbyistFilingPeriodType(models.Model):
    pass


class LobbyistTransactionStatus(models.Model):
    pass


class LobbyistTransactionGroup(models.Model):
    pass
