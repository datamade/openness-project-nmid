from django.db import models

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
    deceased = models.BooleanField()

    def __str__(self):
        name = '{0} {1}'.format(self.first_name, self.last_name)
        return name

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

    def __str__(self):
        return self.name

class Campaign(models.Model):
    olddb_id = models.IntegerField(null=True)
    candidate = models.ForeignKey('Candidate', db_constraint=False)
    election_season = models.ForeignKey('ElectionSeason', db_constraint=False)
    office = models.ForeignKey('Office', db_constraint=False)
    division = models.ForeignKey('Division', db_constraint=False, null=True)
    district = models.ForeignKey('District', db_constraint=False, null=True)
    treasurer = models.ForeignKey('Treasurer', db_constraint=False, null=True)
    status = models.ForeignKey('Status', db_constraint=False, null=True)
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
    

class OfficeType(models.Model):
    description = models.CharField(max_length=50)
    order = models.IntegerField()

class Office(models.Model):
    office_type = models.ForeignKey('OfficeType', db_constraint=False)
    description = models.CharField(max_length=100)
    status = models.ForeignKey('Status', db_constraint=False)
    office_type = models.ForeignKey('OfficeType', db_constraint=False, null=True)
    
    def __str__(self):
        return self.description

class District(models.Model):
    pass

class County(models.Model):
    pass

class PoliticalParty(models.Model):
    pass

class Transaction(models.Model):
    contact = models.ForeignKey('Contact', db_constraint=False, null=True)
    amount = models.FloatField()
    received_date = models.DateTimeField()
    date_added = models.DateTimeField()
    check_number = models.CharField(max_length=50, null=True)
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
    company_name = models.CharField(max_length=255, null=True)
    candidate = models.ForeignKey("Candidate", db_constraint=False, null=True)
    address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=50, null=True)
    state = models.CharField(max_length=25, null=True)
    zipcode = models.CharField(max_length=10, null=True)
    county = models.ForeignKey('County', db_constraint=False, null=True)
    country = models.CharField(max_length=50, null=True)
    contact_type = models.ForeignKey('ContactType', db_constraint=False, null=True)
    transaction_status = models.ForeignKey('Status', db_constraint=False, null=True)
    from_file_id = models.IntegerField(null=True)
    contact_type_other = models.CharField(max_length=25, null=True)
    occupation = models.CharField(max_length=255, null=True)
    expenditure_for_certified_candidate = models.NullBooleanField()

    def __str__(self):
        if self.company_name:
            return self.company_name
        else:
            name = '{0} {1}'.format(self.first_name, self.last_name)
            return name

class TransactionType(models.Model):
    description = models.CharField(max_length=50)
    contribution = models.BooleanField()
    anonymous = models.BooleanField()

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
    edited = models.BooleanField()
    regenerate = models.NullBooleanField()
    
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

class Address(models.Model):
    street = models.CharField(null=True, max_length=100)
    city = models.CharField(null=True, max_length=50)
    state = models.CharField(null=True, max_length=50)
    zip_code = models.CharField(null=True, max_length=10)

    def __str__(self):
        address = '{0}, {1}, {2}, {3}'.format(self.street,
                                              self.city,
                                              self.state,
                                              self.zip_code)
        return address

######################################################################
### Below here are normalized tables that we may or may not end up ###
### getting. Just stubbing them out in case we do                  ###
######################################################################

class RegularFilingPeriod(models.Model):
    pass

class FilingType(models.Model):
    pass

class Entity(models.Model):
    pass

class Status(models.Model):
    pass

class Contact(models.Model):
    pass

class ContactType(models.Model):
    pass

class Treasurer(models.Model):
    pass

class Division(models.Model):
    pass

class ElectionSeason(models.Model):
    pass
