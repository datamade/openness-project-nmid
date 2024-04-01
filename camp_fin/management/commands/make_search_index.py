import os

from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Create search index for New Mexico Campaign Finance data"

    def handle(self, *args, **options):

        self.drop_vector = """
            ALTER TABLE camp_fin_{}
            DROP COLUMN IF EXISTS search_name
        """

        self.add_vector = """
            ALTER TABLE camp_fin_{}
            ADD COLUMN search_name tsvector
        """

        self.populate_vector = """
            UPDATE camp_fin_{0} SET
              search_name = to_tsvector('english', {1})
        """

        self.add_index = """
            CREATE INDEX ON camp_fin_{}
            USING gin(search_name)
        """

        self.create_trigger = """
            CREATE TRIGGER {0}_search_update
            BEFORE INSERT OR UPDATE OF {1} ON camp_fin_{0}
            FOR EACH ROW EXECUTE PROCEDURE
            tsvector_update_trigger(search_name,
                                    'pg_catalog.english', {1})
        """

        self.makeCandidateIndex()
        self.makePACIndex()
        self.makeTransactionIndex()
        self.makeTreasurerIndex()
        self.makeLobbyistIndex()
        self.makeOrganizationIndex()
        self.makeLobbyistTransactionIndex()

        self.stdout.write(self.style.SUCCESS("Worked"))

    def makeCandidateIndex(self):
        index_fields = ["prefix", "first_name", "middle_name", "last_name", "suffix"]

        vector = "concat_ws(' ', {})".format(", ".join(index_fields))

        with transaction.atomic():
            cursor = connection.cursor()
            cursor.execute(self.drop_vector.format("candidate"))
            cursor.execute(self.add_vector.format("candidate"))
            cursor.execute(self.populate_vector.format("candidate", vector))
            cursor.execute(self.add_index.format("candidate"))

            cursor.execute(
                """
                DROP TRIGGER IF EXISTS candidate_search_update
                ON camp_fin_candidate
            """
            )

            cursor.execute(
                self.create_trigger.format("candidate", ",".join(index_fields))
            )

    def makeTreasurerIndex(self):
        index_fields = ["prefix", "first_name", "middle_name", "last_name", "suffix"]

        vector = "concat_ws(' ', {})".format(", ".join(index_fields))

        with transaction.atomic():
            cursor = connection.cursor()
            cursor.execute(self.drop_vector.format("treasurer"))
            cursor.execute(self.add_vector.format("treasurer"))
            cursor.execute(self.populate_vector.format("treasurer", vector))
            cursor.execute(self.add_index.format("treasurer"))

            cursor.execute(
                """
                DROP TRIGGER IF EXISTS treasurer_search_update
                ON camp_fin_treasurer
            """
            )

            cursor.execute(
                self.create_trigger.format("treasurer", ",".join(index_fields))
            )

    def makePACIndex(self):

        with transaction.atomic():
            cursor = connection.cursor()
            cursor.execute(self.drop_vector.format("pac"))
            cursor.execute(self.add_vector.format("pac"))
            cursor.execute(self.populate_vector.format("pac", "COALESCE(name, '')"))
            cursor.execute(self.add_index.format("pac"))

            cursor.execute(
                """
                DROP TRIGGER IF EXISTS pac_search_update
                ON camp_fin_pac
            """
            )

            cursor.execute(self.create_trigger.format("pac", "name"))

    def makeTransactionIndex(self):

        index_fields = [
            "company_name",
            "name_prefix",
            "first_name",
            "middle_name",
            "last_name",
            "suffix",
            "address",
            "city",
            "state",
            "zipcode",
        ]

        vector = "concat_ws(' ', {})".format(", ".join(index_fields))

        with transaction.atomic():
            cursor = connection.cursor()
            cursor.execute(self.drop_vector.format("transaction"))
            cursor.execute(self.add_vector.format("transaction"))
            cursor.execute(self.populate_vector.format("transaction", vector))
            cursor.execute(self.add_index.format("transaction"))

            cursor.execute(
                """
                DROP TRIGGER IF EXISTS transaction_search_update
                ON camp_fin_transaction
            """
            )

            cursor.execute(
                self.create_trigger.format("transaction", ",".join(index_fields))
            )

            this_dir = os.path.abspath(os.path.dirname(__file__))
            file_path = os.path.join(this_dir, "sql", "anonymous_trigger.sql")

            with open(file_path) as f:
                anonymous_trigger = f.read()

            cursor.execute(anonymous_trigger)

            cursor.execute(
                """
                DROP TRIGGER IF EXISTS add_anonymous_transactions
                ON camp_fin_transaction
            """
            )

            cursor.execute(
                """
                CREATE TRIGGER add_anonymous_transactions
                AFTER INSERT OR UPDATE OF {0} ON camp_fin_transaction
                FOR EACH ROW EXECUTE PROCEDURE update_anonymous()
            """.format(
                    ",".join(index_fields)
                )
            )

    def makeLobbyistIndex(self):
        index_fields = ["first_name", "middle_name", "last_name", "suffix"]

        vector = "concat_ws(' ', {})".format(", ".join(index_fields))

        with transaction.atomic():
            cursor = connection.cursor()
            cursor.execute(self.drop_vector.format("lobbyist"))
            cursor.execute(self.add_vector.format("lobbyist"))
            cursor.execute(self.populate_vector.format("lobbyist", vector))
            cursor.execute(self.add_index.format("lobbyist"))

            cursor.execute(
                """
                DROP TRIGGER IF EXISTS lobbyist_search_update
                ON camp_fin_lobbyist
            """
            )

            cursor.execute(
                self.create_trigger.format("lobbyist", ",".join(index_fields))
            )

    def makeLobbyistTransactionIndex(self):
        index_fields = [
            "name",
            "beneficiary",
            "expenditure_purpose",
        ]

        vector = "concat_ws(' ', {})".format(", ".join(index_fields))

        with transaction.atomic():
            cursor = connection.cursor()
            cursor.execute(self.drop_vector.format("lobbyisttransaction"))
            cursor.execute(self.add_vector.format("lobbyisttransaction"))
            cursor.execute(self.populate_vector.format("lobbyisttransaction", vector))
            cursor.execute(self.add_index.format("lobbyisttransaction"))

            cursor.execute(
                """
                DROP TRIGGER IF EXISTS lobbyisttransaction_search_update
                ON camp_fin_lobbyisttransaction
            """
            )

            cursor.execute(
                self.create_trigger.format(
                    "lobbyisttransaction", ",".join(index_fields)
                )
            )

    def makeOrganizationIndex(self):
        with transaction.atomic():
            cursor = connection.cursor()
            cursor.execute(self.drop_vector.format("organization"))
            cursor.execute(self.add_vector.format("organization"))
            cursor.execute(
                self.populate_vector.format("organization", "COALESCE(name, '')")
            )
            cursor.execute(self.add_index.format("organization"))

            cursor.execute(
                """
                DROP TRIGGER IF EXISTS organization_search_update
                ON camp_fin_organization
            """
            )

            cursor.execute(self.create_trigger.format("organization", "name"))
