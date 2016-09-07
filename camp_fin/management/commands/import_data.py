import csv
import zipfile

import sqlalchemy as sa

import psycopg2

from openpyxl import load_workbook

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils.text import slugify

from nmid.typeinferer import TypeInferer
from .table_mappers import CANDIDATE, PAC, FILING, FILING_PERIOD, CONTRIB_EXP, \
    CONTRIB_EXP_TYPE, CAMPAIGN, OFFICE_TYPE, OFFICE, CAMPAIGN_STATUS, COUNTY, \
    DISTRICT, ELECTION_SEASON, ENTITY, ENTITY_TYPE, FILING_TYPE, LOAN, \
    LOAN_TRANSACTION, LOAN_TRANSACTION_TYPE, POLITICAL_PARTY, SPECIAL_EVENT, \
    TREASURER, DIVISION

DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'

engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

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
}

FILE_LOOKUP = {
    'campaign': 'Cam_Campaign.xlsx',
    'transaction': 'Cam_ContribExpenditure.zip',
    'transactiontype': 'Cam_ContribExpenditureType.xlsx',
    'office': 'Cam_ElectionOffice.xlsx',
    'filingperiod': 'Cam_FilingPeriod.xlsx',
    'officetype': 'Cam_OfficeType.xlsx',
    'filing': 'Cam_Report.csv',
    'candidate': 'Candidates.xlsx',
    'pac': 'PACs.xlsx',
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

    def handle(self, *args, **options):
        
        entity_types = options['entity_types'].split(',')
        
        if entity_types == ['all']:
            entity_types = FILE_LOOKUP.keys()

        for entity_type in entity_types:
            self.entity_type = entity_type
            file_name = FILE_LOOKUP.get(entity_type)

            if file_name:
                
                self.stdout.write(self.style.SUCCESS('Importing {}'.format(file_name)))

                self.file_path = 'data/{}'.format(file_name)

                self.encoding = 'utf-8'
                if entity_type == 'transaction':
                    self.encoding = 'windows-1252'

                if self.file_path.endswith('xlsx'):
                    self.convertXLSX()
                
                if self.file_path.endswith('zip'):
                    self.unzipFile()
                
                self.table_mapper = MAPPER_LOOKUP[self.entity_type]

                self.django_table = 'camp_fin_{}'.format(self.entity_type)
                self.raw_pk_col = [k for k, v in self.table_mapper.items() \
                                       if v['field'] == 'id'][0]
                

                self.connection = engine.connect()
                
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

                if self.entity_type in ['candidate', 'pac']:
                    self.populateSlugField()
                    self.stdout.write(self.style.SUCCESS('Populated slug fields for {}'.format(self.entity_type)))
                
                self.stdout.write(self.style.SUCCESS('\n'))
            else:
                self.stdout.write(self.style.ERROR('"{}" is not a valid entity'.format(self.entity_type)))
                self.stdout.write(self.style.SUCCESS('\n'))
            
        self.addTransactionFullName()
        self.addLoanFullName()
        self.addCandidateFullName()

        self.stdout.write(self.style.SUCCESS('Import complete!'.format(self.entity_type)))

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
                id
              FROM camp_fin_transaction
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
                id
              FROM camp_fin_loan
            ) AS s
            WHERE camp_fin_loan.id = s.id
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
                id
              FROM camp_fin_candidate
            ) AS s
            WHERE camp_fin_candidate.id = s.id
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
        
        csv_path = '{}.csv'.format(self.file_path.rsplit('.', 1)[0])
        
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
        if self.entity_type == 'candidate':
            name_components = [
                'first_name', 
                'last_name', 
            ]
            
            selects = []

            for component in name_components:
                select = "COALESCE({}, '')".format(component)
                selects.append(select)

            name_select = " || ' ' || ".join(selects)

        elif self.entity_type == 'pac':
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

        try:
            sql_table = sa.Table('raw_{0}'.format(self.entity_type), 
                                 sa.MetaData(),
                                 autoload=True,
                                 autoload_with=self.connection.engine)
        
        except sa.exc.NoSuchTableError:
            inferer = TypeInferer(self.file_path, encoding=self.encoding)
            inferer.infer()
            
            sql_table = sa.Table('raw_{0}'.format(self.entity_type), 
                                 sa.MetaData())
        
            for column_name, column_type in inferer.types.items():
                sql_table.append_column(sa.Column(column_name.lower().replace('"', ''), column_type()))
        
        dialect = sa.dialects.postgresql.dialect()
        create_table = str(sa.schema.CreateTable(sql_table)\
                           .compile(dialect=dialect)).strip(';')
        
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

    def executeTransaction(self, query, raise_exc=True, *args, **kwargs):
        trans = self.connection.begin()

        try:
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
