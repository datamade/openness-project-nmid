import csv

import sqlalchemy as sa

import psycopg2

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from nmid.typeinferer import TypeInferer
from .table_mappers import CANDIDATE, PAC

DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'

engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

RAW_PK_LOOKUP = {
    'candidate': 'CandidateId',
    'pac': 'PoliticalActionCommitteeId',
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

    def handle(self, *args, **options):

        self.entity_type = options['entity_type']
        self.file_path = options['file_path']
        self.django_table = 'camp_fin_{}'.format(self.entity_type)
        self.raw_pk_col = RAW_PK_LOOKUP[self.entity_type]
        
        if self.entity_type == 'candidate':
            self.table_mapper = CANDIDATE
        elif self.entity_type == 'pac':
            self.table_mapper = PAC

        self.connection = engine.connect()
        
        self.makeRawTable()
        self.importRawData()
        
        self.updateExistingRecords()

        self.makeNewTable()
        self.findNewRecords()
        
        self.addNewRecords()
    
    def addNewRecords(self):
        pass

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
                                  self.table_mappers.keys()])

        dat_fields = ', '.join(['dat.{}'.format(c) for c in \
                                  self.table_mappers.values()])

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
        
        set_fields = ', '.join(['{1}=s."{0}"'.format(k,v) for k,v in \
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
                   entity_type=entity_type,
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
            inferer = TypeInferer(self.file_path)
            inferer.infer()
            
            sql_table = sa.Table('raw_{0}'.format(self.entity_type), 
                                 sa.MetaData())
        
            for column_name, column_type in inferer.types.items():
                sql_table.append_column(sa.Column(column_name, column_type()))
        
        dialect = sa.dialects.postgresql.dialect()
        create_table = str(sa.schema.CreateTable(sql_table)\
                           .compile(dialect=dialect)).strip(';')

        self.executeTransaction('DROP TABLE IF EXISTS raw_{0}'.format(self.entity_type))
        self.executeTransaction(create_table)

    def importRawData(self):
        
        DB_CONN_STR = DB_CONN.format(**settings.DATABASES['default'])

        copy_st = ''' 
            COPY raw_{0} FROM STDIN WITH CSV HEADER DELIMITER ','
        '''.format(self.entity_type)
        
        with open(self.file_path, 'r') as f:
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