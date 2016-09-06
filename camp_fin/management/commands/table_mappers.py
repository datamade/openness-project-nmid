from collections import OrderedDict

CANDIDATE = OrderedDict([
    ('candidateid', {'field': 'id', 'data_type': 'bigint'}),
    ('entityid', {'field': 'entity_id', 'data_type': 'bigint'}),
    ('prefix', {'field': 'prefix', 'data_type': 'varchar'}),
    ('firstname', {'field': 'first_name', 'data_type': 'varchar'}),
    ('lastname', {'field': 'last_name', 'data_type': 'varchar'}),
    ('middlename', {'field': 'middle_name', 'data_type': 'varchar'}),
    ('suffix', {'field': 'suffix', 'data_type': 'varchar'}),
    ('businessphone', {'field': 'business_phone', 'data_type': 'varchar'}),
    ('homephone', {'field': 'home_phone', 'data_type': 'varchar'}),
    ('addressid', {'field': 'address_id', 'data_type': 'bigint'}),
    ('statusid', {'field': 'status_id', 'data_type': 'bigint'}),
    ('dateadded', {'field': 'date_added', 'data_type': 'date'}),
    ('contactid', {'field': 'contact_id', 'data_type': 'bigint'}),
    ('emailaccount', {'field': 'email', 'data_type': 'varchar'}),
    ('datelastupdated', {'field': 'date_updated', 'data_type': 'timestamp with time zone'}),
    ('qualcandidateid', {'field': 'qual_candidate_id', 'data_type': 'bigint'}),
    ('deceased', {'field': 'deceased', 'data_type': 'boolean'}),
])

PAC = OrderedDict([
    ('politicalactioncommitteeid', {'field': 'id', 'data_type': 'bigint'}),
    ('entityid', {'field': 'entity_id', 'data_type': 'bigint'}),
    ('name', {'field': 'name', 'data_type': 'varchar'}),
    ('acronym', {'field': 'acronym', 'data_type': 'varchar'}),
    ('businessphone', {'field': 'business_phone', 'data_type': 'varchar'}),
    ('homephone', {'field': 'home_phone', 'data_type': 'varchar'}),
    ('emailaddress', {'field': 'email', 'data_type': 'varchar'}),
    ('addressid', {'field': 'address_id', 'data_type': 'bigint'}),
    ('treasurerid', {'field': 'treasurer_id', 'data_type': 'bigint'}),
    ('dateadded', {'field': 'date_added', 'data_type': 'date'}),
    ('statusid', {'field': 'status_id', 'data_type': 'bigint'}),
    ('contactid', {'field': 'contact_id', 'data_type': 'bigint'}),
    ('datelastupdated', {'field': 'date_updated', 'data_type': 'timestamp with time zone'}),
    ('bankname', {'field': 'bank_name', 'data_type': 'varchar'}),
    ('bankphone', {'field': 'bank_phone', 'data_type': 'varchar'}),
    ('faxphone', {'field': 'fax_number', 'data_type': 'varchar'}),
    ('bankaddressid', {'field': 'bank_address_id', 'data_type': 'bigint'}),
    ('initialbalance', {'field': 'initial_balance', 'data_type': 'double precision'}),
    ('isinitialbalancesetbypac', {'field': 'initial_balance_from_self', 'data_type': 'boolean'}),
    ('initialdebt', {'field': 'initial_debt', 'data_type': 'money::numeric::double precision'}),
    ('isinitialdebtsetbypac', {'field': 'initial_debt_from_self', 'data_type': 'boolean'}),
])

FILING = OrderedDict([
    ("reportid",{'field': 'id', 'data_type': 'bigint'}),
    ("entityid",{'field': 'entity_id', 'data_type': 'bigint'}),
    ("olddbcampaignid",{'field': 'olddb_campaign_id', 'data_type': 'bigint'}),
    ("olddbprofileitemid",{'field': 'olddb_profile_id', 'data_type': 'bigint'}),
    ("filingperiodid",{'field': 'filing_period_id', 'data_type': 'bigint'}),
    ("statusid",{'field': 'status_id', 'data_type': 'bigint'}),
    ("dateadded",{'field': 'date_added', 'data_type': 'timestamp with time zone'}),
    ("olddbethicsreportid",{'field': 'olddb_ethics_report_id', 'data_type': 'bigint'}),
    ("candidatecampaignid",{'field': 'campaign_id', 'data_type': 'bigint'}),
    ("dateclosed",{'field': 'date_closed', 'data_type': 'timestamp with time zone'}),
    ("lastdateamended",{'field': 'date_last_amended', 'data_type': 'timestamp with time zone'}),
    ("openingbalance",{'field': 'opening_balance', 'data_type': 'money::numeric::double precision'}),
    ("totalcontributionsfp",{'field': 'total_contributions', 'data_type': 'money::numeric::double precision'}),
    ("totalexpendituresfp",{'field': 'total_expenditures', 'data_type': 'money::numeric::double precision'}),
    ("totalloansfp",{'field': 'total_loans', 'data_type': 'money::numeric::double precision'}),
    ("totalinkindcontributionsfp",{'field': 'total_inkind', 'data_type': 'money::numeric::double precision'}),
    ("totalunpaiddebts",{'field': 'total_unpaid_debts', 'data_type': 'money::numeric::double precision'}),
    ("closingbalance",{'field': 'closing_balance', 'data_type': 'money::numeric::double precision'}),
    ("totaldebtcarriedforwardpevfp",{'field': 'total_debt_carried_forward', 'data_type': 'money::numeric::double precision'}),
    ("totaldebtpaidfp",{'field': 'total_debt_paid', 'data_type': 'money::numeric::double precision'}),
    ("totalloansforgivenfp",{'field': 'total_loans_forgiven', 'data_type': 'money::numeric::double precision'}),
    ("pdffile",{'field': 'pdf_report', 'data_type': 'varchar'}),
    ("isfinal",{'field': 'final', 'data_type': 'boolean'}),
    ("isstatementnoactivity",{'field': 'no_activity', 'data_type': 'boolean'}),
    ("supplementalordinalnumber",{'field': 'supplement_count', 'data_type': 'int'}),
    ("totalsupplementalcontributions",{'field': 'total_supplemental_contributions', 'data_type': 'money::numeric::double precision'}),
    ("beenedited",{'field': 'edited', 'data_type': 'boolean'}),
    ("regenerate",{'field': 'regenerate', 'data_type': 'boolean'}),
])

FILING_PERIOD = OrderedDict([
    ("filingperiodid",{'field': 'id', 'data_type': 'bigint'}),
    ("filingdate",{'field': 'filing_date', 'data_type': 'timestamp with time zone'}),
    ("duedate",{'field': 'due_date', 'data_type': 'timestamp with time zone'}),
    ("olddbreportingperiodid",{'field': 'olddb_id', 'data_type': 'bigint'}),
    ("description",{'field': 'description', 'data_type': 'varchar'}),
    ("allowstatementofnoactivity",{'field': 'allow_no_activity', 'data_type': 'boolean'}),
    ("filingperiodtypeid",{'field': 'filing_period_type_id', 'data_type': 'bigint'}),
    ("excludefromcascading",{'field': 'exclude_from_cascading', 'data_type': 'boolean'}),
    ("supplementalinitdate",{'field': 'supplemental_init_date', 'data_type': 'timestamp with time zone'}),
    ("regularfilingperiodid",{'field': 'regular_filing_period_id', 'data_type': 'bigint'}),
    ("initialdate",{'field': 'initial_date', 'data_type': 'date'}),
    ("filingperiodemailingsendstatusid",{'field': 'email_sent_status', 'data_type': 'bigint'}),
    ("filingperiodremindersendstatusid",{'field': 'reminder_sent_status', 'data_type': 'bigint'}),
    # ("dateremindersent",{'field': 'reminder_sent_date', 'data_type': 'date'}),
])

CONTRIB_EXP = OrderedDict([
    ("contribexpenditureid",{'field': 'id', 'data_type': 'bigint'}),
    ("contactid",{'field': 'contact_id', 'data_type': 'bigint'}),
    ("amount",{'field': 'amount', 'data_type': 'money::numeric::double precision'}),
    ("datecontribution",{'field': 'received_date', 'data_type': 'timestamp with time zone'}),
    ("dateadded",{'field': 'date_added', 'data_type': 'timestamp with time zone'}),
    ("checknumber",{'field': 'check_number', 'data_type': 'varchar'}),
    ("memo",{'field': 'memo', 'data_type': 'text'}),
    ("description",{'field': 'description', 'data_type': 'varchar'}),
    ("contribexpendituretypeid",{'field': 'transaction_type_id', 'data_type': 'bigint'}),
    ("reportid",{'field': 'filing_id', 'data_type': 'bigint'}),
    ("olddbcontribexpenditureid",{'field': 'olddb_id', 'data_type': 'bigint'}),
    ("prefix",{'field': 'name_prefix', 'data_type': 'varchar'}),
    ("firstname",{'field': 'first_name', 'data_type': 'varchar'}),
    ("middlename",{'field': 'middle_name', 'data_type': 'varchar'}),
    ("lastname",{'field': 'last_name', 'data_type': 'varchar'}),
    ("suffix",{'field': 'suffix', 'data_type': 'varchar'}),
    ("companyname",{'field': 'company_name', 'data_type': 'varchar'}),
    ("address",{'field': 'address', 'data_type': 'varchar'}),
    ("city",{'field': 'city', 'data_type': 'varchar'}),
    ("state",{'field': 'state', 'data_type': 'varchar'}),
    ("zip",{'field': 'zipcode', 'data_type': 'varchar'}),
    ("countyid",{'field': 'county_id', 'data_type': 'bigint'}),
    ("country",{'field': 'country', 'data_type': 'varchar'}),
    ("contacttypeid",{'field': 'contact_type_id', 'data_type': 'bigint'}),
    ("transactionstatusid",{'field': 'transaction_status_id', 'data_type': 'bigint'}),
    ("fromfileid",{'field': 'from_file_id', 'data_type': 'bigint'}),
    ("contacttypeother",{'field': 'contact_type_other', 'data_type': 'varchar'}),
    ("occupation",{'field': 'occupation', 'data_type': 'varchar'}),
    ("isexpenditureforcertifiedcandidate",{'field': 'expenditure_for_certified_candidate', 'data_type': 'boolean'}),
])

CONTRIB_EXP_TYPE = OrderedDict([
    ("contribexpendituretypeid",{'field': 'id', 'data_type': 'bigint'}),
    ("description",{'field': 'description', 'data_type': 'varchar'}),
    ("iscontribution",{'field': 'contribution', 'data_type': 'boolean'}),
    ("isanonymous", {'field': 'anonymous', 'data_type': 'boolean'}),
])

CAMPAIGN = OrderedDict([
    ("campaignid",{'field': 'id', 'data_type': 'bigint'}),
    ("candidateid",{'field': 'candidate_id', 'data_type': 'bigint'}), 
    ("electionseasonid",{'field': 'election_season_id', 'data_type': 'bigint'}),
    ("electionofficeid",{'field': 'office_id', 'data_type': 'bigint'}),
    ("divisionid",{'field': 'division_id', 'data_type': 'bigint'}),
    ("districtid",{'field': 'district_id', 'data_type': 'bigint'}),
    ("treasurerid",{'field': 'treasurer_id', 'data_type': 'bigint'}),
    ("statusid",{'field': 'status_id', 'data_type': 'bigint'}),
    ("dateadded",{'field': 'date_added', 'data_type': 'timestamp with time zone'}),
    ("countyid",{'field':'county_id', 'data_type': 'bigint'}),
    ("politicalpartyid",{'field': 'political_party_id', 'data_type': 'bigint'}),
    ("datelastupdated",{'field': 'last_updated', 'data_type': 'timestamp with time zone'}),
    ("primaryelectionwinnerstatusid",{'field': 'primary_election_winner_status', 'data_type': 'bigint'}),
    ("generalelectionwinnerstatusid",{'field': 'general_election_winner_status', 'data_type': 'bigint'}),
    ("bankname",{'field': 'bank_name', 'data_type': 'varchar'}),
    ("bankphone",{'field': 'bank_phone', 'data_type': 'varchar'}),
    ("olddbprofileitemid",{'field': 'olddb_id', 'data_type': 'bigint'}),
    ("bankaddressid",{'field': 'bank_address_id', 'data_type': 'bigint'}),
    ("commiteename",{'field': 'committee_name', 'data_type': 'varchar'}),
    ("committeecampaignphone1",{'field': 'committee_phone_1', 'data_type': 'varchar'}),
    ("committeecampaignphone2",{'field': 'committee_phone_2', 'data_type': 'varchar'}),
    ("committeefaxnumber",{'field': 'committee_fax_number', 'data_type': 'varchar'}),
    ("committeeemailaddress",{'field': 'committee_email', 'data_type': 'varchar'}),
    ("committeeaddressid",{'field': 'committee_address_id', 'data_type': 'bigint'}),
    ("initialbalance",{'field': 'initial_balance', 'data_type': 'double precision'}),
    ("isinitialbalancesetbycandidate",{'field': 'initial_balance_from_self', 'data_type': 'boolean'}),
    ("qualcampaignid",{'field': 'qual_campaign_id', 'data_type': 'bigint'}),
    ("initialdebt",{'field': 'initial_debt', 'data_type': 'double precision'}),
    ("isinitialdebtsetbycandidate",{'field': 'initial_debt_from_self', 'data_type': 'boolean'}),
    ("isbiannual",{'field': 'biannual', 'data_type': 'boolean'}),
    ("fromcampaignid",{'field': 'from_campaign_id', 'data_type': 'bigint'}),
])

OFFICE_TYPE = OrderedDict([
    ('officetypeid', {'field': 'id', 'data_type': 'bigint'}),
    ('description', {'field': 'description', 'data_type': 'varchar'}),
])

OFFICE = OrderedDict([
    ("electionofficeid",{'field': 'id', 'data_type': 'bigint'}),
    ("description",{'field': 'description', 'data_type': 'varchar'}),
    ("statusid",{'field': 'status_id', 'data_type': 'bigint'}),
    ("officetypeid",{'field': 'office_type_id', 'data_type': 'bigint'}),
])

CAMPAIGN_STATUS = OrderedDict([
    ("campaignstatusid",{'field': 'id', 'data_type': 'bigint'}),
    ("description",{'field': 'description', 'data_type': 'varchar'}),
])

COUNTY = OrderedDict([
    ("countyid",{'field': 'id', 'data_type': 'bigint'}),
    ("description",{'field': 'name', 'data_type': 'varchar'}),
])

DISTRICT = OrderedDict([
    ("districtid",{'field': 'id', 'data_type': 'bigint'}),
    ("electionofficeid",{'field': 'office_id', 'data_type': 'bigint'}),
    ("description",{'field': 'name', 'data_type': 'varchar'}),
    ("statusid",{'field': 'status_id', 'data_type': 'bigint'}),
])

DIVISION = OrderedDict([
    ("divisionid",{'field': 'id', 'data_type': 'bigint'}),
    ("districtid",{'field': 'district_id', 'data_type': 'bigint'}),
    ("description",{'field': 'name', 'data_type': 'varchar'}),
    ("statusid",{'field': 'status_id', 'data_type': 'bigint'}),
])

ELECTION_SEASON = OrderedDict([
    ("electionseasonid",{'field': 'id', 'data_type': 'bigint'}),
    ("description",{'field': 'year', 'data_type': 'varchar'}),
    ("statusid",{'field': 'status_id', 'data_type': 'bigint'}),
    ("isspecial",{'field': 'special', 'data_type': 'boolean'}),
])

ENTITY = OrderedDict([
    ("entityid",{'field': 'id', 'data_type': 'bigint'}),
    ("userid",{'field': 'user_id', 'data_type': 'bigint'}),
    ("entitytypeid",{'field': 'entity_type_id', 'data_type': 'bigint'}),
    ("olddbentityid",{'field': 'olddb_id', 'data_type': 'bigint'}),
])

ENTITY_TYPE = OrderedDict([
    ("entitytypeid",{'field': 'id', 'data_type': 'bigint'}),
    ("description",{'field': 'description', 'data_type': 'varchar'}),
])

FILING_TYPE = OrderedDict([
    ("filingperiodtypeid",{'field': 'id', 'data_type': 'bigint'}),
    ("description",{'field': 'description', 'data_type': 'varchar'}),
])

LOAN = OrderedDict([
    ("loanid",{'field': 'id', 'data_type': 'bigint'}),
    ("contactid",{'field': 'contact_id', 'data_type': 'bigint'}),
    ("amount",{'field': 'amount', 'data_type': 'double precision'}),
    ("datereceived",{'field': 'received_date', 'data_type': 'timestamp with time zone'}),
    ("dateadded",{'field': 'date_added', 'data_type': 'timestamp with time zone'}),
    ("checknumber",{'field': 'check_number', 'data_type': 'varchar'}),
    ("memo",{'field': 'memo', 'data_type': 'text'}),
    ("reportid",{'field': 'filing_id', 'data_type': 'bigint'}),
    ("olddbloanid",{'field': 'olddb_id', 'data_type': 'bigint'}),
    ("prefix",{'field': 'name_prefix', 'data_type': 'varchar'}),
    ("firstname",{'field': 'first_name', 'data_type': 'varchar'}),
    ("middlename",{'field': 'middle_name', 'data_type': 'varchar'}),
    ("lastname",{'field': 'last_name', 'data_type': 'varchar'}),
    ("suffix",{'field': 'suffix', 'data_type': 'varchar'}),
    ("companyname",{'field': 'company_name', 'data_type': 'varchar'}),
    ("address",{'field': 'address', 'data_type': 'varchar'}),
    ("city",{'field': 'city', 'data_type': 'varchar'}),
    ("state",{'field': 'state', 'data_type': 'varchar'}),
    ("zip",{'field': 'zipcode', 'data_type': 'varchar'}),
    ("countyid",{'field': 'county_id', 'data_type': 'bigint'}),
    ("country",{'field': 'country', 'data_type': 'varchar'}),
    ("contacttypeid",{'field': 'contact_type_id', 'data_type': 'bigint'}),
    ("transactionstatusid",{'field': 'status_id', 'data_type': 'bigint'}),
    ("fromfileid",{'field': 'from_file_id', 'data_type': 'bigint'}),
    ("contacttypeother",{'field': 'contact_type_other', 'data_type': 'varchar'}),
    ("occupation",{'field': 'occupation', 'data_type': 'varchar'}),
    ("loantransferdate",{'field': 'loan_transfer_date', 'data_type': 'timestamp with time zone'}),
    ("interestrate",{'field': 'interest_rate', 'data_type': 'double precision'}),
    ("duedate",{'field': 'due_date', 'data_type': 'timestamp with time zone'}),
    ("paymentscheduleid",{'field': 'payment_schedule_id', 'data_type': 'bigint'}),
])

LOAN_TRANSACTION = OrderedDict([
    ("loantransactionid", {'field': 'id', 'data_type': 'bigint'}),
    ("loanid", {'field': 'loan_id', 'data_type': 'bigint'}),
    ("amount", {'field': 'amount', 'data_type': 'double precision'}),
    ("interestpaid", {'field': 'interest_paid', 'data_type': 'double precision'}),
    ("date", {'field': 'transaction_date', 'data_type': 'timestamp with time zone'}),
    ("dateadded", {'field': 'date_added', 'data_type': 'timestamp with time zone'}),
    ("checknumber", {'field': 'check_number', 'data_type': 'varchar'}),
    ("memo", {'field': 'memo', 'data_type': 'varchar'}),
    ("loantransactiontypeid", {'field': 'transaction_type_id', 'data_type': 'bigint'}),
    ("transactionstatusid", {'field': 'transaction_status_id', 'data_type': 'bigint'}),
    ("reportid", {'field': 'filing_id', 'data_type': 'bigint'}),
    ("fromfileid", {'field': 'from_file_id', 'data_type': 'bigint'}),
])

LOAN_TRANSACTION_TYPE = OrderedDict([
    ("loantransactiontypeid",{'field': 'id', 'data_type': 'bigint'}),
    ("description",{'field': 'description', 'data_type': 'varchar'}),
])

POLITICAL_PARTY = OrderedDict([
    ("politicalpartyid",{'field': 'id', 'data_type': 'bigint'}),
    ("description",{'field': 'name', 'data_type': 'varchar'}),
])

SPECIAL_EVENT = OrderedDict([
    ('specialeventid', {'field': 'id', 'data_type': 'bigint'}),
    ('eventname', {'field': 'event_name', 'data_type': 'varchar'}),
    ('transactionstatusid', {'field': 'transaction_status_id', 'data_type': 'bigint'}),
    ('dateadded', {'field': 'date_added', 'data_type': 'timestamp with time zone'}),
    ('eventdate', {'field': 'event_date', 'data_type': 'timestamp with time zone'}),
    ('admissionprice', {'field': 'admission_price', 'data_type': 'double precision'}),
    ('nbrinattendance', {'field': 'attendance', 'data_type': 'int'}),
    ('eventlocation', {'field': 'location', 'data_type': 'varchar'}),
    ('eventdescription', {'field': 'description', 'data_type': 'varchar'}),
    ('sponsors', {'field': 'sponsors', 'data_type': 'varchar'}),
    ('totaladmissionfee', {'field': 'total_admissions', 'data_type': 'double precision'}),
    ('unidentifiablecontribsanonymous', {'field': 'anonymous_contributions', 'data_type': 'double precision'}),
    ('totalexpenditures', {'field': 'total_expenditures', 'data_type': 'double precision'}),
    ('reportid', {'field': 'filing_id', 'data_type': 'bigint'}),
    ('olddbspecialeventid', {'field': 'olddb_id', 'data_type': 'bigint'}),
    ('olddbspecialeventid', {'field': 'olddb_id', 'data_type': 'bigint'}),
    ("address",{'field': 'address', 'data_type': 'varchar'}),
    ("city",{'field': 'city', 'data_type': 'varchar'}),
    ("zip",{'field': 'zipcode', 'data_type': 'varchar'}),
    ("countyid",{'field': 'county_id', 'data_type': 'bigint'}),
    ("country",{'field': 'country', 'data_type': 'varchar'}),
    ("fromfileid", {'field': 'from_file_id', 'data_type': 'bigint'}),
])

TREASURER = OrderedDict([
    ('treasurerid', {'field': 'id', 'data_type': 'bigint'}),
    ('prefix', {'field': 'prefix', 'data_type': 'varchar'}),
    ('firstname', {'field': 'first_name', 'data_type': 'varchar'}),
    ('lastname', {'field': 'last_name', 'data_type': 'varchar'}),
    ('middlename', {'field': 'middle_name', 'data_type': 'varchar'}),
    ('suffix', {'field': 'suffix', 'data_type': 'varchar'}),
    ('businessphone', {'field': 'business_phone', 'data_type': 'varchar'}),
    ('alternativephone', {'field': 'alt_phone', 'data_type': 'varchar'}),
    ('addressid', {'field': 'address_id', 'data_type': 'bigint'}),
    ('emailaddress', {'field': 'email', 'data_type': 'varchar'}),
    ('dateadded', {'field': 'date_added', 'data_type': 'timestamp with time zone'}),
    ('statusid', {'field': 'status_id', 'data_type': 'bigint'}),
    ('olddbentityid', {'field': 'olddb_entity_id', 'data_type': 'bigint'}),
])
