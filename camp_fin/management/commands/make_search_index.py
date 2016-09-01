from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection

class Command(BaseCommand):
    help = 'Create search index for New Mexico Campaign Finance data'

    # def add_arguments(self, parser):
    #     parser.add_argument(
    #         '--entity-types',
    #         dest='entity_types',
    #         default='all',
    #         help='Comma separated list of entity types to import'
    #     )

    def handle(self, *args, **options):
        self.add_vector = ''' 
            ALTER TABLE camp_fin_{}
            ADD COLUMN search_name tsvector
        '''

        self.populate_vector = ''' 
            UPDATE camp_fin_{0} SET
              search_name = to_tsvector('english', {1})
        '''
        
        self.add_index = ''' 
            CREATE INDEX ON camp_fin_{} 
            USING gin(search_name)
        '''

        self.create_trigger = ''' 
            CREATE TRIGGER {0}_search_update
            BEFORE INSERT OR UPDATE ON camp_fin_{0}
            FOR EACH ROW EXECUTE PROCEDURE
            tsvector_update_trigger(search_name, 
                                    'pg_catalog.english', {1})
        '''
        
        self.makeCandidateIndex()
        self.makePACIndex()
        self.makeTransactionIndex()

        self.stdout.write(self.style.SUCCESS('Worked'))
        
    def makeCandidateIndex(self):
        index_fields = [
            'prefix',
            'first_name',
            'middle_name',
            'last_name',
            'suffix'
        ]

        vector_fields = ["COALESCE({}, '')".format(f) for f in index_fields]

        vector = " || ' ' || ".join(vector_fields)
        
        with transaction.atomic():
            cursor = connection.cursor()

            cursor.execute(self.add_vector.format('candidate'))
            cursor.execute(self.populate_vector.format('candidate', vector))
            cursor.execute(self.add_index.format('candidate'))
            cursor.execute(self.create_trigger.format('candidate', ', '.join(index_fields)))

    def makePACIndex(self):
        pass

    def makeTransactionIndex(self):
        pass
