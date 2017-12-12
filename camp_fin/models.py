from django.db import models
from camp_fin.templatetags.helpers import format_money

class Candidate(models.Model):
    entity = models.ForeignKey("Entity", db_constraint=False)
    prefix = models.CharField(max_length=10, null=True)
    first_name = models.CharField(max_length=50, null=True)
    middle_name = models.CharField(max_length=50, null=True)
    last_name = models.CharField(max_length=50, null=True)
    suffix = models.CharField(max_length=10, null=True)
    business_phone = models.CharField(max_length=50, null=True)
    home_phone = models.CharField(max_length=50, null=True)
    address = models.ForeignKey("Address", null=True, db_constraint=False)
    status = models.ForeignKey("Status", null=True, db_constraint=False)
    date_added = models.DateTimeField(null=True)
    contact = models.ForeignKey("Contact", null=True, db_constraint=False)
    email = models.CharField(max_length=50, null=True)
    date_updated = models.DateTimeField(null=True)
    qual_candidate_id = models.IntegerField(null=True)
    deceased = models.CharField(max_length=3)
    
    full_name = models.CharField(max_length=500, null=True)
    
    slug = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.full_name
    
class PAC(models.Model):
    entity = models.ForeignKey("Entity", db_constraint=False)
    name = models.CharField(max_length=100)
    acronym = models.CharField(max_length=15, null=True)
    business_phone = models.CharField(max_length=20, null=True)
    home_phone = models.CharField(max_length=20, null=True)
    email = models.CharField(max_length=50, null=True)
    address = models.ForeignKey("Address", related_name="address", db_constraint=False, null=True)
    treasurer = models.ForeignKey("Treasurer", db_constraint=False, null=True)
    date_added = models.DateTimeField()
    status = models.ForeignKey("Status", db_constraint=False, null=True)
    contact = models.ForeignKey("Contact", db_constraint=False, null=True)
    date_updated = models.DateTimeField(null=True)
    bank_name = models.CharField(max_length=100, null=True)
    bank_phone = models.CharField(max_length=50, null=True)
    fax_number = models.CharField(max_length=50, null=True)
    bank_address = models.ForeignKey("Address", related_name="pac_bank_address", null=True, db_constraint=False)
    initial_balance = models.FloatField(null=True)
    initial_balance_from_self = models.NullBooleanField(null=True)
    initial_debt = models.FloatField(null=True)
    initial_debt_from_self = models.NullBooleanField(null=True)
    
    slug = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.name
    
    @property
    def full_name(self):
        # This is here so we can treat pacs and candidates the same in
        # templates
        return self.name

class Campaign(models.Model):
    olddb_id = models.IntegerField(null=True)
    candidate = models.ForeignKey('Candidate', db_constraint=False, null=True)
    election_season = models.ForeignKey('ElectionSeason', db_constraint=False)
    office = models.ForeignKey('Office', db_constraint=False)
    division = models.ForeignKey('Division', db_constraint=False, null=True)
    district = models.ForeignKey('District', db_constraint=False, null=True)
    treasurer = models.ForeignKey('Treasurer', db_constraint=False, null=True)
    status = models.ForeignKey('CampaignStatus', db_constraint=False, null=True)
    date_added = models.DateTimeField()
    county = models.ForeignKey('County', db_constraint=False, null=True)
    political_party = models.ForeignKey('PoliticalParty', db_constraint=False)
    last_updated = models.DateTimeField(null=True)
    primary_election_winner_status = models.IntegerField(null=True)
    general_election_winner_status = models.IntegerField(null=True)
    bank_name = models.CharField(max_length=100, null=True)
    bank_phone = models.CharField(max_length=50, null=True)
    bank_address = models.ForeignKey("Address", related_name="campaign_bank_address", null=True, db_constraint=False)
    committee_name = models.CharField(max_length=100, null=True)
    committee_phone_1 = models.CharField(max_length=25, null=True)
    committee_phone_2 = models.CharField(max_length=25, null=True)
    committee_fax_number = models.CharField(max_length=25, null=True)
    committee_email = models.CharField(max_length=50, null=True)
    committee_address = models.ForeignKey('Address', related_name='committee_address', db_constraint=False, null=True)
    initial_balance = models.FloatField(null=True)
    initial_balance_from_self = models.NullBooleanField()
    initial_debt = models.FloatField(null=True)
    initial_debt_from_self = models.NullBooleanField()
    qual_campaign_id = models.IntegerField(null=True)
    biannual = models.NullBooleanField()
    from_campaign = models.ForeignKey('Campaign', db_constraint=False, null=True)
    active_race = models.ForeignKey('Race', db_constraint=False, null=True)

    def __str__(self):
        office = self.office.description

        if self.candidate:
            candidate_name = '{0} {1}'.format(self.candidate.first_name, 
                                            self.candidate.last_name)
            return '{0} ({1})'.format(candidate_name, office)
        else:
            party = self.political_party.name
            return '{0} ({1})'.format(party, office)

    def funds_raised(self, since=None):
        '''
        Total funds raised in a given filing period.

        Accepts an optional filter argument, `since`, as a string representing a year
        (e.g. '2017'). If `since` is present, the method will restrict contributions
        to filings starting January 1st of that year. If `since` is not specified,
        the method will return all contributions ever recorded for this campaign.
        '''
        # Enforce argument format
        assert (since is None or (isinstance(since, str) and len(since) == 4))

        filings = self.candidate.entity.filing_set.all()

        if since:
            date = '{year}-01-01'.format(year=since)
            filings = filings.filter(filing_period__filing_date__gte=date)

        return sum(filing.total_contributions for filing in filings)

    @property
    def is_winner(self):
        if getattr(self, 'race', False):
            # Since the `winner` relationship is OneToOne, the ability
            # to reverse access a `race` (distinct from `active_race`)
            # means that this campaign must be the winner
            return True
        else:
            return False


class Race(models.Model):
    group = models.ForeignKey('RaceGroup', db_constraint=False, null=True)
    office = models.ForeignKey('Office', db_constraint=False)
    division = models.ForeignKey('Division', db_constraint=False, null=True)
    district = models.ForeignKey('District', db_constraint=False, null=True)
    office_type = models.ForeignKey('OfficeType', db_constraint=False, null=True)
    county = models.ForeignKey('County', db_constraint=False, null=True)
    election_season = models.ForeignKey('ElectionSeason', db_constraint=False)
    winner = models.OneToOneField('Campaign', null=True)

    class Meta:
        unique_together = ('district', 'division', 'office_type', 'county',
                           'office', 'election_season')

    def __str__(self):
        return 'Race for {office}'.format(office=self.office)

    @property
    def campaigns(self):
        return self.campaign_set.all()

    @property
    def num_candidates(self):
        return len(self.campaigns)

    @property
    def total_funds(self):
        year = getattr(self.election_season, 'year', None)
        return sum(campaign.funds_raised(since=year) for campaign in self.campaigns)


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
    status = models.ForeignKey('Status', db_constraint=False)
    office_type = models.ForeignKey('OfficeType', db_constraint=False, null=True)
    
    def __str__(self):
        return self.description

class District(models.Model):
    office = models.ForeignKey('Office', db_constraint=False)
    name = models.CharField(max_length=25)
    status = models.ForeignKey('Status', db_constraint=False)

    def __str__(self):
        return '{1} ({0})'.format(self.name, 
                                  self.office.description)

class County(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class PoliticalParty(models.Model):
    name = models.CharField(max_length=25)

    def __str__(self):
        return self.name

class Transaction(models.Model):
    contact = models.ForeignKey('Contact', db_constraint=False, null=True)
    amount = models.FloatField(db_index=True)
    received_date = models.DateTimeField(db_index=True)
    date_added = models.DateTimeField()
    check_number = models.CharField(max_length=100, null=True)
    memo = models.TextField(null=True)
    description = models.CharField(max_length=75, null=True)
    transaction_type = models.ForeignKey('TransactionType', db_constraint=False)
    filing = models.ForeignKey('Filing', db_constraint=False)
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
    zipcode = models.CharField(max_length=10, null=True)
    county = models.ForeignKey('County', db_constraint=False, null=True)
    country = models.CharField(max_length=100, null=True)
    contact_type = models.ForeignKey('ContactType', db_constraint=False, null=True)
    transaction_status = models.ForeignKey('Status', db_constraint=False, null=True)
    from_file_id = models.IntegerField(null=True)
    contact_type_other = models.CharField(max_length=25, null=True)
    occupation = models.CharField(max_length=255, null=True)
    expenditure_for_certified_candidate = models.NullBooleanField()
    
    full_name = models.CharField(max_length=500, null=True)

    def __str__(self):
        return self.full_name
    
    @property
    def transaction_subject(self):
        # This is here so that the API key makes a little more sense
        return self.filing

    @property
    def full_address(self):
        full_address = ''
        
        if self.address:
            full_address = '{}'.format(self.address)
        
        if self.city:
            full_address = '{0} {1}'.format(full_address, self.city)

        if self.state:
            full_address = '{0}, {1}'.format(full_address, self.state)

        if self.zipcode:
            full_address = '{0} {1}'.format(full_address, self.zipcode)

        if self.country:
            full_address = '{0} {1}'.format(full_address, self.country)

        return full_address.strip()

class TransactionType(models.Model):
    description = models.CharField(max_length=50)
    contribution = models.BooleanField()
    anonymous = models.BooleanField()
    
    def __str__(self):
        return self.description

class Loan(models.Model):
    contact = models.ForeignKey('Contact', db_constraint=False, null=True)
    status = models.ForeignKey('Status', db_constraint=False)
    date_added = models.DateTimeField()
    amount = models.FloatField()
    check_number = models.CharField(max_length=30, null=True)
    memo = models.CharField(max_length=500, null=True)
    received_date = models.DateTimeField()
    interest_rate = models.FloatField(null=True)
    due_date = models.DateTimeField(null=True)
    payment_schedule_id = models.IntegerField(null=True)
    filing = models.ForeignKey('Filing', db_constraint=False, null=True)
    olddb_id = models.IntegerField(null=True)
    name_prefix = models.CharField(max_length=25, null=True)
    first_name = models.CharField(max_length=255, null=True)
    middle_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    suffix = models.CharField(max_length=15, null=True)
    company_name = models.CharField(max_length=255, null=True)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=50, null=True)
    state = models.CharField(max_length=25, null=True)
    zipcode = models.CharField(max_length=10, null=True)
    county = models.ForeignKey('County', db_constraint=False, null=True)
    country = models.CharField(max_length=50, null=True)
    contact_type = models.ForeignKey('ContactType', db_constraint=False, null=True)
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
        full_address = ''
        
        if self.address:
            full_address = '{}'.format(self.address)
        
        if self.city:
            full_address = '{0} {1}'.format(full_address, self.city)

        if self.state:
            full_address = '{0}, {1}'.format(full_address, self.state)

        if self.zipcode:
            full_address = '{0} {1}'.format(full_address, self.zipcode)

        if self.country:
            full_address = '{0} {1}'.format(full_address, self.country)

        return full_address.strip()

class LoanTransaction(models.Model):
    loan = models.ForeignKey('Loan', db_constraint=False)
    amount = models.FloatField()
    interest_paid = models.FloatField(null=True)
    transaction_date = models.DateTimeField()
    date_added = models.DateTimeField()
    check_number = models.CharField(max_length=50, null=True)
    memo = models.TextField(null=True)
    transaction_type = models.ForeignKey('LoanTransactionType', db_constraint=False)
    transaction_status = models.ForeignKey('Status', db_constraint=False)
    filing = models.ForeignKey('Filing', db_constraint=False)
    from_file_id = models.IntegerField(null=True)

    def __str__(self):
        return '{0} {1}'.format(self.transaction_type, 
                                format_money(self.amount))

class LoanTransactionType(models.Model):
    description = models.CharField(max_length=25)

    def __str__(self):
        return self.description

class SpecialEvent(models.Model):
    event_name = models.CharField(max_length=255, null=True)
    transaction_status = models.ForeignKey('Status', db_constraint=False)
    date_added = models.DateTimeField()
    event_date = models.DateField()
    admission_price = models.FloatField()
    attendance = models.IntegerField()
    location = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True)
    sponsors = models.TextField(null=True)
    total_admissions = models.FloatField()
    anonymous_contributions = models.FloatField()
    total_expenditures = models.FloatField()
    filing = models.ForeignKey('Filing', db_constraint=False)
    olddb_id = models.IntegerField(null=True)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100, null=True)
    zipcode = models.CharField(max_length=10, null=True)
    county = models.ForeignKey('County', db_constraint=False, null=True)
    country = models.CharField(max_length=50, null=True)
    from_file_id = models.IntegerField(null=True)

    def __str__(self):
        if self.event_name:
            return self.event_name
        else:
            return 'Event sponsored by {0} on {1}'.format(self.sponsors, 
                                                          self.event_date)

class Filing(models.Model):
    entity = models.ForeignKey('Entity', db_constraint=False)
    olddb_campaign_id = models.IntegerField(null=True)
    olddb_profile_id = models.IntegerField(null=True)
    filing_period = models.ForeignKey('FilingPeriod', db_constraint=False)
    status = models.ForeignKey('Status', db_constraint=False, null=True)
    date_added = models.DateTimeField()
    olddb_ethics_report_id = models.IntegerField(null=True)
    campaign = models.ForeignKey('Campaign', db_constraint=False, null=True)
    date_closed = models.DateTimeField()
    date_last_amended = models.DateTimeField(null=True)
    opening_balance = models.FloatField()
    total_contributions = models.FloatField()
    total_expenditures = models.FloatField()
    total_loans = models.FloatField(null=True)
    total_inkind = models.FloatField(null=True)
    total_unpaid_debts = models.FloatField(null=True)
    closing_balance = models.FloatField()
    total_debt_carried_forward = models.FloatField(null=True)
    total_debt_paid = models.FloatField(null=True)
    total_loans_forgiven = models.FloatField(null=True)
    pdf_report = models.CharField(max_length=1000, null=True)
    final = models.BooleanField()
    no_activity = models.BooleanField()
    supplement_count = models.IntegerField(null=True)
    total_supplemental_contributions = models.FloatField(null=True)
    edited = models.CharField(max_length=3)
    regenerate = models.NullBooleanField()
    
    def __str__(self):
        if self.campaign:
            return '{0} {1} {2}'.format(self.campaign.candidate.first_name,
                                        self.campaign.candidate.last_name,
                                        self.filing_period)
        else:
            return self.entity.pac_set.first().name

class FilingPeriod(models.Model):
    filing_date = models.DateTimeField()
    due_date = models.DateTimeField()
    olddb_id = models.IntegerField(null=True)
    description = models.CharField(max_length=255, null=True)
    allow_no_activity = models.BooleanField()
    filing_period_type = models.ForeignKey('FilingType', db_constraint=False)
    exclude_from_cascading = models.BooleanField()
    supplemental_init_date = models.DateTimeField(null=True)
    regular_filing_period = models.ForeignKey('RegularFilingPeriod', db_constraint=False, null=True)
    initial_date = models.DateField()
    email_sent_status = models.IntegerField()
    reminder_sent_status = models.IntegerField()
    
    def __str__(self):
        return '{0}/{1} ({2})'.format(self.filing_date.month, 
                                      self.filing_date.year,
                                      self.filing_period_type.description)

class Address(models.Model):
    street = models.CharField(null=True, max_length=255)
    city = models.CharField(null=True, max_length=255)
    state = models.ForeignKey('State', null=True, db_constraint=False)
    zipcode = models.CharField(null=True, max_length=10)
    county = models.ForeignKey('County', null=True, db_constraint=False)
    country = models.CharField(max_length=50, null=True)
    address_type = models.ForeignKey('AddressType', null=True, db_constraint=False)
    olddb_id = models.IntegerField(null=True)
    date_added = models.DateTimeField(null=True)
    from_file_id = models.IntegerField(null=True)

    def __str__(self):
        address = '{0} {1}, {2} {3}'.format(self.street,
                                            self.city,
                                            self.state,
                                            self.zipcode)
        return address

class CampaignStatus(models.Model):
    description = models.CharField(max_length=10)

    def __str__(self):
        return self.description

class Division(models.Model):
    name = models.CharField(max_length=25)
    district = models.ForeignKey('District', db_constraint=False)
    status = models.ForeignKey('Status', db_constraint=False)

    def __str__(self):
        return '{0} ({1})'.format(self.name, self.district)

class ElectionSeason(models.Model):
    year = models.CharField(max_length=5)
    special = models.BooleanField()
    status = models.ForeignKey('Status', db_constraint=False)

    def __str__(self):
        return 'Election year {}'.format(self.year)

class Entity(models.Model):
    user_id = models.IntegerField(null=True)
    entity_type = models.ForeignKey('EntityType', db_constraint=False, null=True)
    olddb_id = models.IntegerField(null=True)
    
    def __str__(self):
        return 'Entity {}'.format(self.entity_type)

class EntityType(models.Model):
    description = models.CharField(max_length=25)

    def __str__(self):
        return self.description

class FilingType(models.Model):
    description = models.CharField(max_length=25)
    
    def __str__(self):
        return self.description

class Treasurer(models.Model):
    prefix = models.CharField(max_length=10, null=True)
    first_name = models.CharField(max_length=50, null=True)
    middle_name = models.CharField(max_length=50, null=True)
    last_name = models.CharField(max_length=50, null=True)
    suffix = models.CharField(max_length=10, null=True)
    business_phone = models.CharField(max_length=50, null=True)
    alt_phone = models.CharField(max_length=50, null=True)
    email = models.CharField(max_length=255, null=True)
    address = models.ForeignKey('Address', db_constraint=False)
    date_added = models.DateTimeField()
    status = models.ForeignKey('Status', db_constraint=False)
    olddb_entity_id = models.IntegerField(null=True)

    full_name = models.CharField(max_length=500, null=True)
    
    def __str__(self):
        return self.full_name

class Contact(models.Model):
    prefix = models.CharField(max_length=10, null=True)
    first_name = models.CharField(max_length=50, null=True)
    middle_name = models.CharField(max_length=50, null=True)
    last_name = models.CharField(max_length=50, null=True)
    suffix = models.CharField(max_length=10, null=True)
    occupation = models.CharField(max_length=100, null=True)
    address = models.ForeignKey('Address', db_constraint=False)
    phone = models.CharField(max_length=30, null=True)
    email = models.CharField(max_length=100, null=True)
    memo = models.TextField(null=True)
    company_name = models.CharField(max_length=255, null=True)
    contact_type = models.ForeignKey('ContactType', db_constraint=False)
    status = models.ForeignKey('Status', db_constraint=False)
    olddb_id = models.IntegerField(null=True)
    date_added = models.DateTimeField(null=True)
    entity = models.ForeignKey('Entity', db_constraint=False)
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
        return ''
######################################################################
### Below here are normalized tables that we may or may not end up ###
### getting. Just stubbing them out in case we do                  ###
######################################################################

class RegularFilingPeriod(models.Model):
    pass

class Status(models.Model):
    pass

class AddressType(models.Model):
    pass
