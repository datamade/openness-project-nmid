import csv

import sqlalchemy as sa

import psycopg2

from openpyxl import load_workbook

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from nmid.typeinferer import TypeInferer
from .table_mappers import CANDIDATE, PAC, FILING, FILING_PERIOD, CONTRIB_EXP, \
    CONTRIB_EXP_TYPE, CAMPAIGN, OFFICE_TYPE, OFFICE

DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'

engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

RAW_PK_LOOKUP = {
    'candidate': 'candidateid',
    'pac': 'politicalactioncommitteeid',
    'filing': 'reportid',
    'filingperiod': 'filingperiodid',
    'transaction': 'contribexpenditureid',
    'transactiontype': 'contribexpendituretypeid',
    'campaign': 'campaignid',
    'officetype': 'officetypeid',
    'office': 'electionofficeid',
}

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
}

class Command(BaseCommand):
    help = 'Import New Mexico Campaign Finance data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--entity-type',
            dest='entity_type',
            required=True,
            help='Entity type in referenced file'
        )

        parser.add_argument(
            '--file-path',
            dest='file_path',
            required=True,
            help='Relative path to file to load'
        )
        parser.add_argument(
            '--encoding', 
            dest='encoding',
            default='utf-8',
            help='File encoding (defaults to UTF-8)'
        )


    def handle(self, *args, **options):

        self.entity_type = options['entity_type']
        self.file_path = options['file_path']
        self.encoding = options['encoding']

        if self.file_path.endswith('xlsx'):
            self.convertXLSX()

        self.django_table = 'camp_fin_{}'.format(self.entity_type)
        self.raw_pk_col = RAW_PK_LOOKUP[self.entity_type]
        
        self.table_mapper = MAPPER_LOOKUP[self.entity_type]

        self.connection = engine.connect()
        
        self.makeRawTable()
        self.importRawData()
        
        self.updateExistingRecords()

        self.makeNewTable()
        self.findNewRecords()
        
        self.addNewRecords()
        
        # This should only be necessary until we get the actual entity table
        
        if self.entity_type in ['candidate', 'pac', 'filing']:
            self.populateEntityTable()

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
        
        raw_fields = ', '.join(['raw."{}"'.format(c) for c in \
                                  self.table_mapper.keys()])

        dat_fields = ', '.join(['dat.{}'.format(c['field']) for c in \
                                  self.table_mapper.values()])

        where_clause = '''
            WHERE md5(({raw_fields})::text) != md5(({dat_fields})::text)
        '''.format(raw_fields=raw_fields, dat_fields=dat_fields)

        find_changes = ''' 
            INSERT INTO change_{entity_type}
              SELECT raw."{raw_pk_col}" AS id
              FROM raw_{entity_type} AS raw
              JOIN {django_table} AS dat
                ON raw."{raw_pk_col}" = dat.id
              {where_clause}
        '''.format(entity_type=self.entity_type,
                   raw_pk_col=self.raw_pk_col,
                   django_table=self.django_table,
                   where_clause=where_clause)

        self.executeTransaction(find_changes)
        
        set_fields = ', '.join(['{1}=s."{0}"::{2}'.format(k,v['field'], v['data_type']) for k,v in \
                                    self.table_mapper.items()])

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
            next(f)
            with psycopg2.connect(DB_CONN_STR) as conn:
                with conn.cursor() as curs:
                    try:
                        curs.copy_expert(copy_st, f)
                    except psycopg2.IntegrityError as e:
                        logger.error(e, exc_info=True)
                        print(e)
                        conn.rollback()
        
        self.executeTransaction('''
            ALTER TABLE raw_{0} ADD PRIMARY KEY ("{1}")
        '''.format(self.entity_type, self.raw_pk_col))

    def executeTransaction(self, query, raise_exc=False, *args, **kwargs):
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
            print(e)
            if raise_exc:
                raise e
