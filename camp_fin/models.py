from django.db import models

class Candidate(models.Model):
    entity = models.ForeignKey("Entity")
    prefix = models.CharField(max_length=10, null=True)
    first_name = models.CharField(max_length=20, null=True)
    middle_name = models.CharField(max_length=20, null=True)
    last_name = models.CharField(max_length=20, null=True)
    suffix = models.CharField(max_length=10, null=True)
    business_phone = models.CharField(max_length=20, null=True)
    home_phone = models.CharField(max_length=20, null=True)
    address = models.ForeignKey("Address", null=True)
    status = models.ForeignKey("Status", null=True)
    date_added = models.DateTimeField(null=True)
    contact = models.ForeignKey("Contact", null=True)
    email = models.CharField(max_length=50, null=True)
    date_updated = models.DateTimeField(null=True)
    qual_candidate_id = models.IntegerField(null=True)
    deceased = models.BooleanField()

    def __str__(self):
        name = '{0} {1}'.format(self.first_name, self.last_name)
        return name

class PAC(models.Model):
    entity = models.ForeignKey("Entity")
    name = models.CharField(max_length=100)
    acronym = models.CharField(max_length=15, null=True)
    business_phone = models.CharField(max_length=20, null=True)
    home_phone = models.CharField(max_length=20, null=True)
    email = models.CharField(max_length=50, null=True)
    address = models.ForeignKey("Address", related_name="address")
    treasurer = models.ForeignKey("Treasurer")
    date_added = models.DateTimeField()
    status = models.ForeignKey("Status")
    contact = models.ForeignKey("Contact")
    date_updated = models.DateTimeField(null=True)
    bank = models.CharField(max_length=100, null=True)
    bank_phone = models.CharField(max_length=50, null=True)
    fax_number = models.CharField(max_length=50, null=True)
    bank_address = models.ForeignKey("Address", related_name="bank_address", null=True)
    initial_balance = models.FloatField(null=True)
    initial_balance_from_self = models.NullBooleanField(null=True)
    initial_debt = models.FloatField(null=True)
    initial_debt_from_self = models.NullBooleanField(null=True)

    def __str__(self):
        return self.name

class Contribution(models.Model):
    received_date = models.DateField()
    date_added = models.DateTimeField()
    first_name = models.CharField(max_length=255, null=True)
    middle_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    company_name = models.CharField(max_length=255, null=True)
    candidate = models.ForeignKey("Candidate")
    address = models.ForeignKey("Address")
    occupation = models.CharField(max_length=255, null=True)
    filing = models.ForeignKey("Filing")
    # contribution_type comes from the description field from the bulk download.
    contribution_type = models.CharField(max_length=100)
    amount = models.FloatField()
    memo = models.TextField(null=True)

    def __str__(self):
        if self.company_name:
            return self.company_name
        else:
            name = '{0} {1}'.format(self.first_name, self.last_name)
            return name

class Expenditure(models.Model):
    expended_date = models.DateField()
    date_added = models.DateTimeField()
    first_name = models.CharField(max_length=255, null=True)
    middle_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    company_name = models.CharField(max_length=255, null=True)
    candidate = models.ForeignKey("Candidate")
    address = models.ForeignKey("Address")
    occupation = models.CharField(max_length=255, null=True)
    filing = models.ForeignKey("Filing")
    amount = models.FloatField()
    memo = models.TextField(null=True)

    def __str__(self):
        if self.company_name:
            return self.company_name
        else:
            name = '{0} {1}'.format(self.first_name, self.last_name)
            return name

class Filing(models.Model):
    opening_balance = models.FloatField()
    closing_balance = models.FloatField()
    filing_date = models.DateField()
    received_date = models.DateTimeField()

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

class Entity(models.Model):
    pass

class Status(models.Model):
    pass

class Contact(models.Model):
    pass

class Treasurer(models.Model):
    pass


