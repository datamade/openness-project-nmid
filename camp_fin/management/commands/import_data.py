from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.db.utils import ProgrammingError

class Command(BaseCommand):
    help = 'Import New Mexico Campaign Finance data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--entity_types',
            dest='entity_types',
            default='candidate,pac',
            help='Comma separated list of entity types'
        )

    def handle(self, *args, **options):

        entity_types = options['entity_types'].split(',')

        print(entity_types)


