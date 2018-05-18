import os
import csv
import zipfile
from datetime import datetime, timedelta

import sqlalchemy as sa

import psycopg2

from openpyxl import load_workbook

import pytz

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils.text import slugify

from .table_mappers import *

DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'

engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

# Field mappings are defined in `table_mappers.py`
MAPPER_LOOKUP = {
    'candidate': CANDIDATE,
    'pac': PAC,
    'filing': FILING,
    'filingperiod': FILING_PERIOD,
    'transaction': CONTRIB_EXP,
    'transactiontype': CONTRIB_EXP_TYPE,
    'campaign': CAMPAIGN,
    'officetype': OFFICE_TYPE,
    'office': OFFICE,
    'campaignstatus': CAMPAIGN_STATUS,
    'county': COUNTY,
    'district': DISTRICT,
    'division': DIVISION,
    'electionseason': ELECTION_SEASON,
    'entity': ENTITY,
    'entitytype': ENTITY_TYPE,
    'filingtype': FILING_TYPE,
    'loan': LOAN,
    'loantransaction': LOAN_TRANSACTION,
    'loantransactiontype': LOAN_TRANSACTION_TYPE,
    'politicalparty': POLITICAL_PARTY,
    'specialevent': SPECIAL_EVENT,
    'treasurer': TREASURER,
    'address': ADDRESS,
    'contacttype': CONTACT_TYPE,
    'contact': CONTACT,
    'state': STATE,
    'lobbyist': LOBBYIST,
    'lobbyistregistration': LOBBYIST_REGISTRATION,
    'lobbyistemployer': LOBBYIST_EMPLOYER,
    'organization': ORGANIZATION,
    'lobbyistfilingperiod': LOBBYIST_FILING_PERIOD,
    'lobbyisttransaction': LOBBYIST_TRANSACTION,
    'lobbyisttransactiontype': LOBBYIST_TRANSACTION_TYPE,
    'lobbyistbundlingdisclosure': LOBBYIST_BUNDLING_DISCLOSURE,
    'lobbyistbundlingdisclosurecontributor': LOBBYIST_BUNDLING_DISCLOSURE_CONTRIBUTOR,
    'lobbyistreport': LOBBYIST_REPORT,
    'lobbyistspecialevent': LOBBYIST_SPECIAL_EVENT,
}

FILE_LOOKUP = {
    'campaign': 'Cam_Campaign.xlsx',
    'transaction': 'cam_ContribExpenditure.zip',
    'transactiontype': 'Cam_ContribExpenditureType.xlsx',
    'office': 'Cam_ElectionOffice.xlsx',
    'filingperiod': 'Cam_FilingPeriod.xlsx',
    'officetype': 'Cam_OfficeType.xlsx',
    'filing': 'Cam_Report.xlsx',
    'candidate': 'Cam_Candidate.xlsx',
    'pac': 'Cam_PoliticalActionCommittee.xlsx',
    'campaignstatus': 'Cam_CampaignStatus.xlsx',
    'county': 'Cam_County.xlsx',
    'district': 'Cam_District.xlsx',
    'division': 'Cam_Division.xlsx',
    'electionseason': 'Cam_ElectionSeason.xlsx',
    'entity': 'Cam_Entity.xlsx',
    'entitytype': 'Cam_EntityType.xlsx',
    'filingtype': 'Cam_FilingPeriodType.xlsx',
    'loan': 'Cam_Loan.xlsx',
    'loantransaction': 'Cam_LoanTransaction.xlsx',
    'loantransactiontype': 'Cam_LoanTransactionType.xlsx',
    'politicalparty': 'Cam_PoliticalParty.xlsx',
    'specialevent': 'Cam_SpecialEvent.xlsx',
    'treasurer': 'Cam_Treasurer.xlsx',
    'address': 'Cam_Address.csv',
    'contacttype': 'Cam_ContactType.xlsx',
    'contact': 'Cam_Contact.csv',
    'state': 'States.csv',
    'lobbyist': 'Cam_Lobbyist.xlsx',
    'lobbyistregistration': 'Cam_LobbystRegistration.xlsx',
    'lobbyistemployer': 'Cam_LobbyistEmployer.xlsx',
    'organization': 'Cam_Organization.xlsx',
    'lobbyistfilingperiod': 'Cam_FilingPeriodLobbyist.xlsx',
    'lobbyisttransaction': 'Cam_ContribExpenditureLobbyist.xlsx',
    'lobbyisttransactiontype': 'Cam_ContribExpenditureLobbyistType.xlsx',
    'lobbyistbundlingdisclosure': 'Cam_BundlingDisclosureLobbyist.xlsx',
    'lobbyistbundlingdisclosurecontributor': 'Cam_BundlingDisclosureLobbyistContributor.xlsx',
    'lobbyistreport': 'Cam_ReportLobbyist.xlsx',
    'lobbyistspecialevent': 'Cam_SpecialEventLobbyist.xlsx',
}

class Command(BaseCommand):
    help = 'Import New Mexico Campaign Finance data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--entity-types',
            dest='entity_types',
            default='all',
            help='Comma separated list of entity types to import'
        )

        parser.add_argument(
            '--add-aggregates',
            dest='add_aggregates',
            action='store_true',
            help='Just add the aggregates'
        )

    def handle(self, *args, **options):

        self.connection = engine.connect()

        if options['add_aggregates']:
            self.makeTransactionAggregates()
            self.stdout.write(self.style.SUCCESS('Aggregates complete!'))
            return

        entity_types = options['entity_types'].split(',')

        if entity_types == ['all']:
            entity_types = FILE_LOOKUP.keys()

        self.makeETLTracker()

        for entity_type in entity_types:
            self.doETL(entity_type)

            self.updateTracker(entity_type)

        self.addTransactionFullName()
        self.addLoanFullName()
        self.addCandidateFullName()
        self.addContactFullName()
        self.addTreasurerFullName()

        # Make or refresh materialized views
        self.makeTransactionAggregates()
        self.stdout.write(self.style.SUCCESS('Made transaction aggregate views'))

        self.stdout.write(self.style.SUCCESS('Import complete!'.format(self.entity_type)))

    def doETL(self, entity_type):
        self.entity_type = entity_type
        file_name = FILE_LOOKUP.get(entity_type)

        if file_name:

            self.stdout.write(self.style.SUCCESS('Importing {}'.format(file_name)))

            self.file_path = 'data/{}'.format(file_name)

            ftp_file = os.path.join(settings.FTP_DIRECTORY, file_name)

            if os.path.exists(ftp_file):
                self.file_path = ftp_file

            self.encoding = 'utf-8'
            if entity_type in ['transaction', 'address', 'contact', 'campaign']:
                self.encoding = 'windows-1252'

            if self.file_path.endswith('xlsx'):
                self.convertXLSX()

            if self.file_path.endswith('zip'):
                self.unzipFile()

            self.table_mapper = MAPPER_LOOKUP[self.entity_type]

            self.django_table = 'camp_fin_{}'.format(self.entity_type)
            self.raw_pk_col = [k for k, v in self.table_mapper.items() \
                                   if v['field'] == 'id'][0]

            self.makeRawTable()
            count = self.importRawData()

            self.stdout.write(self.style.SUCCESS('Found {0} records in {1}'.format(count, file_name)))

            count = self.updateExistingRecords()

            self.stdout.write(self.style.SUCCESS('Updated {0} records in {1}'.format(count, self.django_table)))

            self.makeNewTable()
            count = self.findNewRecords()

            self.addNewRecords()

            self.stdout.write(self.style.SUCCESS('Inserted {0} new records into {1}'.format(count, self.django_table)))

            # This should only be necessary until we get the actual entity table

            if self.entity_type in ['candidate', 'pac', 'filing']:
                self.populateEntityTable()
                self.stdout.write(self.style.SUCCESS('Populated entity table for {}'.format(self.entity_type)))

            if self.entity_type in ['candidate', 'pac', 'lobbyist', 'organization']:
                self.populateSlugField()
                self.stdout.write(self.style.SUCCESS('Populated slug fields for {}'.format(self.entity_type)))

            if self.entity_type == 'loan':
                self.makeLoanBalanceView()
                self.stdout.write(self.style.SUCCESS('Made loan balance view'))

            self.stdout.write(self.style.SUCCESS('\n'))

        else:
            self.stdout.write(self.style.ERROR('"{}" is not a valid entity'.format(self.entity_type)))
            self.stdout.write(self.style.SUCCESS('\n'))

    def makeTransactionAggregates(self):

        for interval in ['day', 'week', 'month']:
            try:
                self.executeTransaction('''
                    REFRESH MATERIALIZED VIEW contributions_by_{}
                '''.format(interval))
            except sa.exc.ProgrammingError:
                view = '''
                    CREATE MATERIALIZED VIEW contributions_by_{0} AS (
                      SELECT
                        SUM(amount) AS amount,
                        entity_id,
                        {0}
                      FROM (
                        SELECT
                          SUM(t.amount) AS amount,
                          f.entity_id,
                          MAX(date_trunc('{0}', t.received_date)) AS {0}
                        FROM camp_fin_transaction AS t
                        JOIN camp_fin_transactiontype AS tt
                          ON t.transaction_type_id = tt.id
                        JOIN camp_fin_filing AS f
                          ON t.filing_id = f.id
                        WHERE tt.contribution = TRUE
                          AND (tt.description = 'Monetary contribution' or
                               tt.description = 'Anonymous Contribution')
                        GROUP BY f.entity_id, date_trunc('{0}', t.received_date)
                        UNION
                        SELECT
                          SUM(l.amount) AS amount,
                          f.entity_id,
                          MAX(date_trunc('{0}', l.received_date)) AS {0}
                        FROM camp_fin_loan AS l
                        JOIN camp_fin_filing AS f
                          ON l.filing_id = f.id
                        GROUP BY f.entity_id, date_trunc('{0}', l.received_date)
                      ) AS s
                      GROUP BY entity_id, {0}
                    )
                '''.format(interval)

                self.executeTransaction(view)

            try:
                self.executeTransaction('''
                    REFRESH MATERIALIZED VIEW expenditures_by_{}
                '''.format(interval))
            except sa.exc.ProgrammingError:
                view = '''
                    CREATE MATERIALIZED VIEW expenditures_by_{0} AS (
                      SELECT
                        entity_id,
                        SUM(amount) AS amount,
                        {0}
                      FROM (
                        SELECT
                          filing.entity_id,
                          SUM(e.amount) AS amount,
                          date_trunc('{0}', e.received_date) AS {0}
                        FROM camp_fin_transaction AS e
                        JOIN camp_fin_transactiontype AS tt
                          ON e.transaction_type_id = tt.id
                        JOIN camp_fin_filing AS filing
                          ON e.filing_id = filing.id
                        JOIN camp_fin_filingperiod AS fp
                          ON filing.filing_period_id = fp.id
                        WHERE tt.contribution = FALSE
                          AND fp.filing_date >= '2010-01-01'
                        GROUP BY filing.entity_id, date_trunc('{0}', e.received_date)

                        UNION

                        SELECT
                          filing.entity_id,
                          SUM(lt.amount) AS amount,
                          date_trunc('{0}', lt.transaction_date) AS {0}
                        FROM camp_fin_loantransaction AS lt
                        JOIN camp_fin_loantransactiontype AS ltt
                          ON lt.transaction_type_id = ltt.id
                        JOIN camp_fin_filing AS filing
                          ON lt.filing_id = filing.id
                        JOIN camp_fin_filingperiod AS fp
                          ON filing.filing_period_id = fp.id
                        WHERE ltt.description = 'Payment'
                          AND fp.filing_date >= '2010-01-01'
                        GROUP BY filing.entity_id, date_trunc('{0}', lt.transaction_date)
                      ) AS s
                      GROUP BY entity_id, {0}
                    )
                '''.format(interval)

                self.executeTransaction(view)


    def makeETLTracker(self):
        create = '''
            CREATE TABLE IF NOT EXISTS etl_tracker (
              id SERIAL,
              entity_type VARCHAR,
              last_update timestamp with time zone,
              PRIMARY KEY (id)
            )
        '''
        self.executeTransaction(create)

    def updateTracker(self, entity_type):
        update = '''
            INSERT INTO etl_tracker (
              entity_type,
              last_update
            ) VALUES (
              :entity_type,
              NOW()
            )
        '''
        self.executeTransaction(sa.text(update),
                                entity_type=entity_type)

    def loadLoanTransactions(self):
        timezone = pytz.timezone(settings.TIME_ZONE)

        transactions_updated = self.connection.execute('''
            SELECT MAX(last_update) AS last_update
            FROM etl_tracker
            WHERE entity_type = 'loantransaction'
        ''').first().last_update

        if transactions_updated:
            an_hour_ago = timezone.localize(datetime.now()) - timedelta(hours=1)
            if transactions_updated < an_hour_ago:
                self.doETL('loantransaction')
        else:
            self.doETL('loantransaction')

    def makeAllExpenditureView(self):
        self.loadLoanTransactions()

        view = '''
            SELECT
              transaction.filing_id,
              transaction.id,
              transaction.amount,
              transaction.full_name,
              transaction_type.description,
              transaction_type.contribution
            FROM camp_fin_transaction AS transaction
            JOIN camp_fin_transactiontype AS transaction_type
              ON transaction.transaction_type_id = transaction_type.id
            WHERE transaction_type.contribution = FALSE
            UNION
            SELECT
              loan_transaction.filing_id,
              loan_transaction.id,
              loan_transaction.amount,
              loan.full_name,
              loan_transaction_type.description,
              FALSE as contribution
            FROM camp_fin_loantransaction AS loan_transaction
            JOIN camp_fin_loantransactiontype AS loan_transaction_type
              ON loan_transaction.transaction_type_id = loan_transaction_type.id
            JOIN camp_fin_loan AS loan
              ON loan_transaction.loan_id = loan.id
            WHERE loan_transaction_type.description = 'Payment'
        '''

    def makeLoanBalanceView(self):
        self.loadLoanTransactions()

        try:
            self.executeTransaction('''
                REFRESH MATERIALIZED VIEW current_loan_status
            ''', raise_exc=True)
        except sa.exc.ProgrammingError:
            self.executeTransaction('''
                CREATE MATERIALIZED VIEW current_loan_status AS (
                  SELECT
                    loan.id AS loan_id,
                    MAX(loan.amount) AS loan_amount,
                    SUM(loantrans.amount) AS payments_made,
                    (MAX(loan.amount) - SUM(loantrans.amount)) AS outstanding_balance
                  FROM camp_fin_loan AS loan
                  JOIN camp_fin_loantransaction AS loantrans
                    ON loan.id = loantrans.loan_id
                  GROUP BY loan.id
                  HAVING ((MAX(loan.amount::numeric::money) - SUM(loantrans.amount::numeric::money)) > 0::money)
                )
            ''')

    def addTransactionFullName(self):
        update = '''
            UPDATE camp_fin_transaction SET
              full_name = s.full_name
            FROM (
              SELECT
                CASE WHEN
                  company_name IS NULL OR TRIM(company_name) = ''
                THEN
                  TRIM(concat_ws(' ',
                                 name_prefix,
                                 first_name,
                                 middle_name,
                                 last_name,
                                 suffix))
                ELSE
                  company_name
                END AS full_name,
                t.id
              FROM camp_fin_transaction AS t
              LEFT JOIN change_transaction AS c
                ON t.id = c.id
              LEFT JOIN new_transaction AS n
                ON t.id = n.id
              WHERE c.id IS NOT NULL
                OR n.id IS NOT NULL
            ) AS s
            WHERE camp_fin_transaction.id = s.id
        '''

        self.executeTransaction(update)

    def addLoanFullName(self):
        update = '''
            UPDATE camp_fin_loan SET
              full_name = s.full_name
            FROM (
              SELECT
                CASE WHEN
                  company_name IS NULL OR TRIM(company_name) = ''
                THEN
                  TRIM(concat_ws(' ',
                                 name_prefix,
                                 first_name,
                                 middle_name,
                                 last_name,
                                 suffix))
                ELSE
                  company_name
                END AS full_name,
                t.id
              FROM camp_fin_loan AS t
              LEFT JOIN change_loan AS c
                ON t.id = c.id
              LEFT JOIN new_loan AS n
                ON t.id = n.id
              WHERE c.id IS NOT NULL
                OR n.id IS NOT NULL
            ) AS s
            WHERE camp_fin_loan.id = s.id
        '''

        self.executeTransaction(update)

    def addTreasurerFullName(self):
        update = '''
            UPDATE camp_fin_treasurer SET
              full_name = s.full_name
            FROM (
              SELECT
                  TRIM(concat_ws(' ',
                                 prefix,
                                 first_name,
                                 middle_name,
                                 last_name,
                                 suffix)) AS full_name,
                t.id
              FROM camp_fin_treasurer AS t
              LEFT JOIN change_treasurer AS c
                ON t.id = c.id
              LEFT JOIN new_treasurer AS n
                ON t.id = n.id
              WHERE c.id IS NOT NULL
                OR n.id IS NOT NULL
            ) AS s
            WHERE camp_fin_treasurer.id = s.id
        '''

        self.executeTransaction(update)

    def addCandidateFullName(self):
        update = '''
            UPDATE camp_fin_candidate SET
              full_name = s.full_name
            FROM (
              SELECT
                  TRIM(concat_ws(' ',
                                 prefix,
                                 first_name,
                                 middle_name,
                                 last_name,
                                 suffix)) AS full_name,
                t.id
              FROM camp_fin_candidate AS t
              LEFT JOIN change_candidate AS c
                ON t.id = c.id
              LEFT JOIN new_candidate AS n
                ON t.id = n.id
              WHERE c.id IS NOT NULL
                OR n.id IS NOT NULL
            ) AS s
            WHERE camp_fin_candidate.id = s.id
        '''

        self.executeTransaction(update)

    def addContactFullName(self):
        update = '''
            UPDATE camp_fin_contact SET
              full_name = s.full_name
            FROM (
              SELECT
                CASE WHEN
                  company_name IS NULL OR TRIM(company_name) = ''
                THEN
                  TRIM(concat_ws(' ',
                                 prefix,
                                 first_name,
                                 middle_name,
                                 last_name,
                                 suffix))
                ELSE
                  company_name
                END AS full_name,
                t.id
              FROM camp_fin_contact AS t
              LEFT JOIN change_contact AS c
                ON t.id = c.id
              LEFT JOIN new_contact AS n
                ON t.id = n.id
              WHERE c.id IS NOT NULL
                OR n.id IS NOT NULL
            ) AS s
            WHERE camp_fin_contact.id = s.id
        '''

        self.executeTransaction(update)


    def unzipFile(self):
        file_name = self.file_path.split('/')[1].rsplit('.', 1)[0]
        file_name = '{}.csv'.format(file_name)
        with zipfile.ZipFile(self.file_path) as zf:
            zf.extract(file_name, path='data')

        self.file_path = 'data/{}'.format(file_name)

    def convertXLSX(self):
        wb = load_workbook(self.file_path)
        sheet = wb.get_active_sheet()

        header = [r.value for r in sheet.rows[0]]

        base_name = os.path.basename(self.file_path.rsplit('.', 1)[0])
        csv_path = '{}.csv'.format(os.path.join('data', base_name))

        with open(csv_path, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for row in sheet.rows[1:]:
                row_values = [r.value for r in row]
                writer.writerow(row_values)

        self.file_path = csv_path

    def populateEntityTable(self):
        entities = '''
            INSERT INTO camp_fin_entity
              SELECT DISTINCT d.entity_id
              FROM {table} AS d
              LEFT JOIN camp_fin_entity AS e
                ON d.entity_id = e.id
              WHERE e.id IS NULL
        '''.format(table=self.django_table)

        self.executeTransaction(entities)

    def populateSlugField(self):
        if self.entity_type in ['candidate', 'lobbyist']:
            name_components = [
                'first_name',
                'last_name',
            ]

            selects = []

            for component in name_components:
                select = "COALESCE({}, '')".format(component)
                selects.append(select)

            name_select = " || ' ' || ".join(selects)

        elif self.entity_type in ['pac', 'organization']:
            name_select = 'name'

        slugify = '''
            UPDATE {django_table} SET
              slug = s.slug
            FROM (
              SELECT
                regexp_replace(TRANSLATE(REPLACE(LOWER({name_select}), ' ', '-'), 'áàâãäåāăąÁÂÃÄÅĀĂĄèééêëēĕėęěĒĔĖĘĚìíîïìĩīĭÌÍÎÏÌĨĪĬóôõöōŏőÒÓÔÕÖŌŎŐùúûüũūŭůÙÚÛÜŨŪŬŮ','aaaaaaaaaaaaaaaaaeeeeeeeeeeeeeeeiiiiiiiiiiiiiiiiooooooooooooooouuuuuuuuuuuuuuuu'), '[^\w -]', '', 'g') || '-' || id::varchar as slug,
                id
              FROM {django_table}
            ) AS s
            WHERE {django_table}.id = s.id
        '''.format(django_table=self.django_table,
                   name_select=name_select)

        self.executeTransaction(slugify)

    def addNewRecords(self):

        select_fields = ', '.join(['raw."{0}"::{2} AS {1}'.format(k,v['field'], v['data_type']) for k,v in \
                                    self.table_mapper.items()])

        dat_fields = ', '.join([c['field'] for c in self.table_mapper.values()])

        insert_new = '''
            INSERT INTO {django_table} (
              {dat_fields}
            )
              SELECT {select_fields}
              FROM raw_{entity_type} AS raw
              JOIN new_{entity_type} AS new
                ON raw."{raw_pk_col}" = new.id
        '''.format(django_table=self.django_table,
                   dat_fields=dat_fields,
                   select_fields=select_fields,
                   entity_type=self.entity_type,
                   raw_pk_col=self.raw_pk_col)

        self.executeTransaction(insert_new)

    def updateExistingRecords(self):
        changes = '''
            CREATE TABLE change_{} (
                id BIGINT,
                PRIMARY KEY (id)
            )
        '''.format(self.entity_type)

        self.executeTransaction('DROP TABLE IF EXISTS change_{}'.format(self.entity_type))
        self.executeTransaction(changes)

        wheres = []

        for raw_col, mapping in self.table_mapper.items():
            condition = '''
                ((raw."{0}" IS NOT NULL OR dat.{1} IS NOT NULL) AND raw."{0}"::{2} <> dat.{1})
            '''.format(raw_col, mapping['field'], mapping['data_type'])
            wheres.append(condition)

        where_clause = ' OR '.join(wheres)

        find_changes = '''
            INSERT INTO change_{entity_type}
              SELECT raw."{raw_pk_col}" AS id
              FROM raw_{entity_type} AS raw
              JOIN {django_table} AS dat
                ON raw."{raw_pk_col}" = dat.id
              WHERE {where_clause}
        '''.format(entity_type=self.entity_type,
                   raw_pk_col=self.raw_pk_col,
                   django_table=self.django_table,
                   where_clause=where_clause)

        self.executeTransaction(find_changes)

        set_fields = ', '.join(['{1}=s."{0}"::{2}'.format(k,v['field'], v['data_type']) for k,v in \
                                    self.table_mapper.items()])

        raw_fields = ', '.join(['raw."{}"'.format(c) for c in \
                                  self.table_mapper.keys()])
        update_dat = '''
            UPDATE {django_table} SET
              {set_fields}
            FROM (
              SELECT {raw_fields}
              FROM raw_{entity_type} AS raw
              JOIN change_{entity_type} AS change
                ON raw."{raw_pk_col}" = change.id
            ) AS s
            WHERE {django_table}.id = s."{raw_pk_col}"
        '''.format(django_table=self.django_table,
                   set_fields=set_fields,
                   raw_fields=raw_fields,
                   entity_type=self.entity_type,
                   raw_pk_col=self.raw_pk_col)

        self.executeTransaction(update_dat)

        change_count = self.connection.execute('SELECT COUNT(*) AS count FROM change_{}'.format(self.entity_type))

        return change_count.first().count

    def findNewRecords(self):

        find = '''
            INSERT INTO new_{entity_type}
              SELECT raw."{raw_pk_col}" AS id
              FROM raw_{entity_type} AS raw
              LEFT JOIN {django_table} AS dat
                ON raw."{raw_pk_col}" = dat.id
              WHERE dat.id IS NULL
        '''.format(entity_type=self.entity_type,
                   django_table=self.django_table,
                   raw_pk_col=self.raw_pk_col)

        self.executeTransaction(find)

        new_count = self.connection.execute('SELECT COUNT(*) AS count FROM new_{}'.format(self.entity_type))
        return new_count.first().count

    def makeNewTable(self):
        create = '''
            CREATE TABLE new_{0} (
                id BIGINT,
                PRIMARY KEY (id)
            )
        '''.format(self.entity_type)

        self.executeTransaction('DROP TABLE IF EXISTS new_{0}'.format(self.entity_type))
        self.executeTransaction(create)

    def makeRawTable(self):

        with open(self.file_path, 'r', encoding=self.encoding) as f:
            reader = csv.reader(f)
            fields = next(reader)

        fields = ', '.join(['"{}" VARCHAR'.format(f.lower()) for f in fields \
                                if f.lower() != self.raw_pk_col])

        create_table = '''
            CREATE TABLE raw_{0} (
                {1} BIGINT,
                {2},
                PRIMARY KEY ({1})
            )
        '''.format(self.entity_type,
                   self.raw_pk_col,
                   fields)


        self.executeTransaction('DROP TABLE IF EXISTS raw_{0}'.format(self.entity_type))
        self.executeTransaction(create_table)

    def importRawData(self):

        DB_CONN_STR = DB_CONN.format(**settings.DATABASES['default'])

        copy_st = '''
            COPY raw_{0} FROM STDIN WITH CSV HEADER
        '''.format(self.entity_type)

        with open(self.file_path, 'r', encoding=self.encoding) as f:
            with psycopg2.connect(DB_CONN_STR) as conn:
                with conn.cursor() as curs:
                    try:
                        curs.copy_expert(copy_st, f)
                    except psycopg2.IntegrityError as e:
                        logger.error(e, exc_info=True)
                        conn.rollback()

        self.executeTransaction('''
            ALTER TABLE raw_{0} ADD PRIMARY KEY ("{1}")
        '''.format(self.entity_type, self.raw_pk_col), raise_exc=False)

        import_count = self.connection.execute('SELECT COUNT(*) AS count FROM raw_{}'.format(self.entity_type))

        return import_count.first().count

    def executeTransaction(self, query, *args, **kwargs):
        trans = self.connection.begin()

        raise_exc = kwargs.get('raise_exc', True)

        try:
            self.connection.execute("SET local timezone to 'America/Denver'")
            if kwargs:
                self.connection.execute(query, **kwargs)
            else:
                self.connection.execute(query, *args)
            trans.commit()
        except sa.exc.ProgrammingError as e:
            # TODO: Make some kind of logger
            # logger.error(e, exc_info=True)
            trans.rollback()
            if raise_exc:
                raise e
