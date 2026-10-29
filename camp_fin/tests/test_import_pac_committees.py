import csv
import tempfile

from django.core.management import call_command
from django.test import TransactionTestCase

from camp_fin.models import PAC

FIELDNAMES = ["CommitteeName", "CommitteeType", "StateID", "MemberID", "IdNumber"]


def write_pac_csv(rows):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)
    f.close()
    return f.name


class ImportPacCommitteesTestCase(TransactionTestCase):
    def test_reimport_links_existing_pac_by_name_when_no_state_id(self):
        """
        Running the import twice for a PAC with no state id should link
        back to the same PAC by name, rather than creating a duplicate.
        """
        path = write_pac_csv(
            [
                {
                    "CommitteeName": "Friends of New Mexico",
                    "CommitteeType": "PAC",
                    "StateID": "",
                    "MemberID": "member-one",
                    "IdNumber": "member-one",
                },
            ]
        )

        call_command("import_pac_committees", file=path)
        call_command("import_pac_committees", file=path)

        pacs = PAC.objects.filter(name="Friends of New Mexico")
        self.assertEqual(pacs.count(), 1)

    def test_name_collision_without_state_id_does_not_raise(self):
        """
        Two distinct PACs sharing a name and lacking a state id can't be
        told apart from PAC committee data alone (member id isn't a
        reliable cross-file join key). Importing should not crash; it
        should link to one of them and log a warning for manual review.
        """
        first_path = write_pac_csv(
            [
                {
                    "CommitteeName": "Friends of New Mexico",
                    "CommitteeType": "PAC",
                    "StateID": "",
                    "MemberID": "member-one",
                    "IdNumber": "member-one",
                },
            ]
        )
        call_command("import_pac_committees", file=first_path)

        # Force a second, distinct PAC with the same name directly, the
        # way it could already exist from historical (pre-fix) data.
        from django.utils.crypto import get_random_string

        from camp_fin.models import Entity, EntityType

        entity_type = EntityType.objects.get(description="PAC")
        other_entity = Entity.objects.create(entity_type=entity_type)
        PAC.objects.create(
            name="Friends of New Mexico",
            slug=f"friends-of-new-mexico-{get_random_string(5)}",
            entity=other_entity,
        )

        second_path = write_pac_csv(
            [
                {
                    "CommitteeName": "Friends of New Mexico",
                    "CommitteeType": "PAC",
                    "StateID": "",
                    "MemberID": "member-two",
                    "IdNumber": "member-two",
                },
            ]
        )

        # Should not raise, despite two PACs matching by name.
        call_command("import_pac_committees", file=second_path)

        self.assertEqual(PAC.objects.filter(name="Friends of New Mexico").count(), 2)

    def test_pac_with_state_id_is_linked_by_state_id(self):
        path = write_pac_csv(
            [
                {
                    "CommitteeName": "State Linked PAC",
                    "CommitteeType": "PAC",
                    "StateID": "1234",
                    "MemberID": "member-three",
                    "IdNumber": "member-three",
                },
            ]
        )

        call_command("import_pac_committees", file=path)

        pac = PAC.objects.get(name="State Linked PAC")
        self.assertEqual(pac.entity.user_id, 1234)

        call_command("import_pac_committees", file=path)
        self.assertEqual(
            PAC.objects.filter(entity__user_id=1234).count(),
            1,
        )
