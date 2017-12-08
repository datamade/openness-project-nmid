from django.core.management.base import BaseCommand
from django.conf import settings
import sqlalchemy as sa


DB_CONN = 'postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}'

engine = sa.create_engine(DB_CONN.format(**settings.DATABASES['default']),
                          convert_unicode=True,
                          server_side_cursors=True)

class Command(BaseCommand):
    help = 'Make materialized views for contested races.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recreate',
            action='store_true',
            dest='recreate',
            default=False,
            help='Drop and recreate views'
        )

    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS('Creating materialized view for races...'))

        conn = engine.connect()

        recreate = options['recreate']

        if recreate:
            conn.execute('''
                DROP MATERIALIZED VIEW camp_fin_races
            ''')

        create_view = '''
            CREATE MATERIALIZED VIEW camp_fin_races
            AS (
              SELECT
                dist.name AS district,
                div.name AS division,
                ofc.ofctype AS office_type,
                ofc.office AS office,
                ARRAY_AGG(DISTINCT cand.full_name) AS candidates,
                COUNT(cand.full_name) AS candidate_count,
                SUM(cand.closing_balance) AS funds
              FROM camp_fin_campaign AS camp
              LEFT JOIN camp_fin_district AS dist
                ON(dist.id = camp.district_id)
              LEFT JOIN camp_fin_division AS div
                ON(div.id = camp.division_id)
              LEFT JOIN (
                SELECT
                  camp_fin_office.id AS id,
                  camp_fin_office.description AS office,
                  camp_fin_officetype.description AS ofctype
                FROM camp_fin_office
                LEFT JOIN camp_fin_officetype
                ON(camp_fin_officetype.id = camp_fin_office.office_type_id)
              ) AS ofc
                ON(ofc.id = camp.office_id)
              LEFT JOIN (
                SELECT
                  DENSE_RANK() OVER (ORDER BY closing_balance DESC) AS rank,
                  cands.*
                FROM (
                  SELECT DISTINCT ON (candidate.id)
                    candidate.*,
                    filing.closing_balance
                  FROM camp_fin_candidate AS candidate
                  JOIN camp_fin_filing AS filing
                    USING(entity_id)
                  WHERE filing.date_added >= '2010-01-01'
                ) AS cands
              ) AS cand
                ON(cand.id = camp.candidate_id)
              WHERE camp.election_season_id = 17 -- 2014; update for 2018!
              GROUP BY (district, division, office_type, office)
              ORDER BY district, division, office_type, office
            )
        '''

        try:
            conn.execute(create_view)
        except sa.exc.ProgrammingError as e:
            if 'relation "camp_fin_races" already exists' in str(e):
                self.stdout.write(self.style.WARNING('Materialized view already exists.'))
                self.stdout.write(self.style.SUCCESS('Refreshing materialized view...'))
                conn.execute('''REFRESH MATERIALIZED VIEW camp_fin_races''')
                verb = 'Refreshed'
            else:
                raise(e)
        else:
            verb = 'Created'

        self.stdout.write(self.style.SUCCESS('%s view!' % verb))

        conn.close()
