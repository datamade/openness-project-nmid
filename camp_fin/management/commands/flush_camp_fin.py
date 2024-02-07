import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Flush campaign finance data from the database, preserving pages and user auth."
    )

    def handle(self, *args, **options):

        this_dir = os.path.abspath(os.path.dirname(__file__))
        file_path = os.path.join(this_dir, "sql", "flush.sql")

        self.stdout.write(
            self.style.SUCCESS("Flushing database using SQL file %s" % file_path)
        )

        self.execute_sql(file_path)

        self.stdout.write(self.style.SUCCESS("Database flushed!"))

    def execute_sql(self, file_path):
        """
        Execute arbitrary SQL code from a file location.
        """
        with open(file_path) as f:
            statements = f.read().split(";")

            with connection.cursor() as cursor:
                for statement in statements:
                    if statement != "\n":  # Skip empty lines
                        cursor.execute(statement.strip())
