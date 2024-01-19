	"OrgID" TEXT,
	"Transaction Amount" TEXT,
	"Transaction Date" DATE,
	"Last Name" TEXT,
	"First Name" TEXT,
	"Middle Name" TEXT,
	"Prefix" TEXT,
	"Suffix" TEXT,
	"Contributor Address Line 1" TEXT,
	"Contributor Address Line 2" TEXT,
	"Contributor City" TEXT,
	"Contributor State" TEXT,
	"Contributor Zip Code" TEXT,
	"Description" TEXT,
	"Check Number" TEXT,
	"Transaction ID" TEXT,
	"Filed Date" DATE,
	"Election" TEXT,
	"Report Name" TEXT,
	"Start of Period" TEXT,
	"End of Period" TEXT,
	"Contributor Code" TEXT,
	"Contribution Type" TEXT,
	"Report Entity Type" TEXT,
	"Committee Name" TEXT,
	"Candidate Last Name" TEXT,
	"Candidate First Name" TEXT,
	"Candidate Middle Name" TEXT,
	"Candidate Prefix" TEXT,
	"Candidate Suffix" TEXT,
	"Amended" TEXT,
	"Contributor Employer" TEXT,
	"Contributor Occupation" TEXT,
	"Occupation Comment" TEXT,
	"Employment Information Requested" TEXT


/* CREATE CONTRIBUTORS */

/* Lookup */
DROP TABLE IF EXISTS contributor_lookup;

CREATE TABLE contributor_lookup AS
SELECT
	"Transaction ID",
	MD5(CONCAT("Prefix", "First Name", "Middle Name", "Last Name", "Suffix", "Contributor Address Line 1", "Contributor Address Line 2", "Contributor City", "Contributor State", "Contributor Zip Code")) AS entity_id,
	"Prefix",
	"First Name",
	"Middle Name",
	"Last Name",
	"Suffix",
	"Contributor Occupation",
	"Contributor Employer",
	"Contributor Code",
	CONCAT_WS(', ', "Contributor Address Line 1", "Contributor Address Line 2") AS street, 
	"Contributor City", 
	"Contributor State", 
	"Contributor Zip Code"
FROM :table_name;

/* Entity Type */
INSERT INTO camp_fin_entitytype (description)
SELECT DISTINCT "Contributor Code" 
FROM contributor_lookup cl 
LEFT JOIN camp_fin_entitytype et 
ON cl."Contributor Code" = et.description 
WHERE et.description IS NULL
	AND cl."Contributor Code" IS NOT NULL;

/* Entity */
INSERT INTO camp_fin_entity (user_id, entity_type_id)
SELECT DISTINCT ON (entity_id)
	cl.entity_id,
	et.id
FROM contributor_lookup cl
JOIN camp_fin_entitytype et
ON cl."Contributor Code" = et.description
LEFT JOIN camp_fin_entity e
ON cl.entity_id = e.user_id
WHERE e.user_id IS NULL;

/* Address */
INSERT INTO camp_fin_address (street, city, state_id, zipcode)
SELECT DISTINCT
	cl.street, 
	"Contributor City", 
	s.id, 
	"Contributor Zip Code"
FROM contributor_lookup cl
LEFT JOIN camp_fin_state s
ON cl."Contributor State" = s.postal_code
LEFT JOIN camp_fin_address a
ON cl.street = a.street 
	AND cl."Contributor City" = a.city 
	AND cl."Contributor Zip Code" = a.zipcode
WHERE a.street IS NULL 
	AND a.city IS NULL 
	AND a.zipcode IS NULL
	AND cl.street != '';

/* Contact Type */
INSERT INTO camp_fin_contacttype (description)
SELECT DISTINCT "Contributor Code" 
FROM contributor_lookup cl
LEFT JOIN camp_fin_contacttype ct 
ON cl."Contributor Code" = ct.description 
WHERE ct.description IS NULL
	AND cl."Contributor Code" IS NOT NULL;

/* Contact */
INSERT INTO camp_fin_contact (prefix, first_name, middle_name, last_name, suffix, address_id, occupation, company_name, contact_type_id, entity_id, status_id)
SELECT DISTINCT
	"Prefix",
	"First Name",
	"Middle Name",
	"Last Name",
	"Suffix",
	a.id,
	"Contributor Occupation",
	"Contributor Employer",
	ct.id,
	e.id,
	0
FROM contributor_lookup cl
JOIN camp_fin_address a
ON cl.street = a.street
	AND "Contributor City" = a.city 
	AND "Contributor Zip Code" = a.zipcode
JOIN camp_fin_contacttype ct 
	ON cl."Contributor Code" = ct.description
JOIN camp_fin_entity e
ON cl.entity_id = e.user_id
LEFT JOIN camp_fin_contact c
ON c.entity_id = e.id
WHERE e.id IS NULL;

/* CREATE FILINGS */

/* PAC Lookup */
CREATE TABLE pac_lookup AS
SELECT
	"Transaction ID",
	"OrgID",
	"Committee Name",
	"Report Entity Type"
FROM :table_name;

/* Entity type */
INSERT INTO camp_fin_entitytype (description)
SELECT DISTINCT "Report Entity Type" 
FROM pac_lookup pl 
LEFT JOIN camp_fin_entitytype et 
ON pl."Report Entity Type" = et.description 
WHERE et.description IS NULL
	AND pl."Report Entity Type" IS NOT NULL;

/* Entity */
INSERT INTO camp_fin_entity (user_id, entity_type_id)
SELECT DISTINCT ON ("OrgID")
	"OrgID",
	et.id
FROM pac_lookup pl
JOIN camp_fin_entitytype et
ON pl."Report Entity Type" = et.description
LEFT JOIN camp_fin_entity e
ON pl."OrgID" = e.user_id
WHERE e.user_id IS NULL;

/* PAC */
INSERT INTO camp_fin_pac (entity_id, name)
SELECT DISTINCT ON ("OrgID")
	e.id,
	"Committee Name"
FROM pac_lookup pl
JOIN camp_fin_entity e
ON pl."OrgID" = e.user_id
LEFT JOIN camp_fin_pac p
ON p.entity_id = e.id
WHERE e.id IS NULL;

/* Candidate Lookup */
CREATE TABLE candidate_lookup AS
SELECT
	"Transaction ID",
	MD5(CONCAT("Candidate Prefix", "Candidate First Name", "Candidate Middle Name", "Candidate Last Name", "Candidate Suffix")) AS entity_id,
	"Candidate Prefix",
	"Candidate First Name",
	"Candidate Middle Name",
	"Candidate Last Name",
	"Candidate Suffix",
	CONCAT_WS(' ', "Candidate Prefix", "Candidate First Name", "Candidate Middle Name", "Candidate Last Name", "Candidate Suffix") AS full_name
FROM :table_name;

/* Entity type */
INSERT INTO camp_fin_entitytype (description)
SELECT 'Candidate'
WHERE NOT EXISTS (
	SELECT 1 FROM camp_fin_entitytype
	WHERE description = 'Candidate'
)

/* Entity */
INSERT INTO camp_fin_entity (user_id, entity_type_id)
SELECT DISTINCT ON (entity_id)
	entity_id,
	et.id
FROM candidate_lookup cl
JOIN camp_fin_entitytype et
ON et.description = 'Candidate'
LEFT JOIN camp_fin_entity e
ON cl.entity_id = e.user_id
WHERE e.user_id IS NULL;

/* Candidate */
INSERT INTO camp_fin_candidate (entity_id, prefix, first_name, middle_name, last_name, suffix, full_name)
SELECT DISTINCT
	e.id,
	"Candidate Prefix",
	"Candidate First Name",
	"Candidate Middle Name",
	"Candidate Last Name",
	"Candidate Suffix",
	cl.full_name
FROM candidate_lookup cl
JOIN camp_fin_entity e
ON cl.entity_id = e.user_id
LEFT JOIN camp_fin_candidate c
ON e.id = c.entity_id
WHERE c.entity_id IS NULL
	AND cl.full_name != '';

/* Filing lookup */
CREATE TABLE filing_lookup AS
SELECT
	"Transaction ID",
	"OrgID",
	"Committee Name",
	MD5(CONCAT("Candidate Prefix", "Candidate First Name", "Candidate Middle Name", "Candidate Last Name", "Candidate Suffix")) AS candidate_entity_id,
	"Report Entity Type",
	"Report Name",
	"Start of Period",
	"End of Period",
	"Filed Date"
FROM :table_name;

/* Filing period */
INSERT INTO camp_fin_filingperiod (description, initial_date, due_date, filing_date, allow_no_activity, exclude_from_cascading, email_sent_status, filing_period_type_id)
SELECT DISTINCT ON ("Report Name", "Start of Period", "End of Period", "Filed Date")
	"Report Name",
	"Start of Period"::DATE,
	"End of Period"::DATE,
	"Filed Date"::DATE,
	False,
	False,
	0,
	0
FROM filing_lookup fl
LEFT JOIN camp_fin_filingperiod fp
ON fl."Report Name" = fp.description
	AND fl."Start of Period"::DATE = fp.initial_date
	AND fl."End of Period"::DATE = fp.due_date
	AND fl."Filed Date"::DATE = fp.filing_date
WHERE fp.id IS NULL;

/* Campaign */
INSERT INTO camp_fin_campaign (candidate_id, committee_name, office_id, election_season_id, date_added, political_party_id)
SELECT DISTINCT
	cand.id,
	fl."Committee Name", 
	1, /* TODO: Fix */
	1, /* TODO: Fix */
	NOW(),
	1
FROM filing_lookup fl
JOIN camp_fin_entity cand_e
ON fl.candidate_entity_id = cand_e.user_id
JOIN camp_fin_candidate cand
ON cand_e.id = cand.entity_id
LEFT JOIN camp_fin_campaign camp
ON cand.id = camp.candidate_id
	AND fl."Committee Name" = camp.committee_name
WHERE camp.id IS NULL;

/* Filing */
INSERT INTO camp_fin_filing (entity_id, filing_period_id, campaign_id, date_added)
SELECT DISTINCT
	CASE
		WHEN fl."Report Entity Type" = 'Candidate' THEN cand_e.id
		ELSE pac_e.id
	END AS filing_entity_id,
	fp.id AS filing_period_id,
	camp.id,
	NOW()
FROM filing_lookup fl
LEFT JOIN camp_fin_entity cand_e
ON fl.candidate_entity_id = cand_e.user_id
LEFT JOIN camp_fin_entity pac_e
ON fl."OrgID" = pac_e.user_id
JOIN camp_fin_filingperiod fp
ON fl."Report Name" = fp.description
	AND fl."Start of Period"::DATE = fp.initial_date
	AND fl."End of Period"::DATE = fp.due_date
	AND fl."Filed Date"::DATE = fp.filing_date
LEFT JOIN camp_fin_candidate cand
ON cand.entity_id = cand_e.id
LEFT JOIN camp_fin_campaign camp
ON cand.id = camp.candidate_id
	AND fl."Committee Name" = camp.committee_name


SELECT
	fl."Transaction ID",
	f.id
FROM filing_lookup fl
LEFT JOIN camp_fin_entity cand_e
ON fl.candidate_entity_id = cand_e.user_id
LEFT JOIN camp_fin_entity pac_e
ON fl."OrgID" = pac_e.user_id
JOIN camp_fin_filingperiod fp
ON fl."Report Name" = fp.description
	AND fl."Start of Period"::DATE = fp.initial_date
	AND fl."End of Period"::DATE = fp.due_date
	AND fl."Filed Date"::DATE = fp.filing_date
LEFT JOIN camp_fin_candidate cand
ON cand.entity_id = cand_e.id
LEFT JOIN camp_fin_campaign camp
ON cand.id = camp.candidate_id
	AND fl."Committee Name" = camp.committee_name
JOIN camp_fin_filing f
ON f.filing_period_id = fp.id
AND f.entity_id = (CASE
	WHEN fl."Report Entity Type" = 'Candidate' THEN cand_e.id
	ELSE pac_e.id
END)
AND f.campaign_id = camp.id

INSERT INTO camp_fin_transaction (contact_id, address, city, state, zipcode, amount, received_date, check_number, description, full_name, name_prefix, first_name, middle_name, last_name, suffix, company_name, occupation, filing_id, transaction_type_id, date_added)
SELECT DISTINCT ON ("Transaction ID")
	con.id,
	a.street,
	a.city,
	s.postal_code,
	a.zipcode,
	con_2023."Transaction Amount"::numeric,
	con_2023."Transaction Date",
	con_2023."Check Number",
	LEFT(con_2023."Description", 75),
	con.full_name,
	con.prefix,
	con.first_name,
	con.middle_name,
	con.last_name,
	con.suffix,
	con.company_name,
	con.occupation,
	filing.id,
	(SELECT id FROM camp_fin_transactiontype WHERE description = 'Monetary contribution'),
	NOW()
FROM con_2023
JOIN contributor_lookup cl
USING ("Transaction ID")
JOIN camp_fin_entity con_e
ON cl.entity_id = con_e.user_id
JOIN camp_fin_contact con
ON con.entity_id = con_e.id
JOIN camp_fin_address a
ON con.address_id = a.id
JOIN camp_fin_state s
ON a.state_id = s.id
JOIN (
	SELECT
		fl."Transaction ID",
		f.id
	FROM filing_lookup fl
	LEFT JOIN camp_fin_entity cand_e
	ON fl.candidate_entity_id = cand_e.user_id
	LEFT JOIN camp_fin_entity pac_e
	ON fl."OrgID" = pac_e.user_id
	JOIN camp_fin_filingperiod fp
	ON fl."Report Name" = fp.description
		AND fl."Start of Period"::DATE = fp.initial_date
		AND fl."End of Period"::DATE = fp.due_date
		AND fl."Filed Date"::DATE = fp.filing_date
	LEFT JOIN camp_fin_candidate cand
	ON cand.entity_id = cand_e.id
	LEFT JOIN camp_fin_campaign camp
	ON cand.id = camp.candidate_id
		AND fl."Committee Name" = camp.committee_name
	JOIN camp_fin_filing f
	ON f.filing_period_id = fp.id
	AND f.entity_id = (CASE
		WHEN fl."Report Entity Type" = 'Candidate' THEN cand_e.id
		ELSE pac_e.id
	END)
	AND f.campaign_id = camp.id
) filing
USING ("Transaction ID")