from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("camp_fin", "0094_entity_member_id"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="entity",
            name="member_id",
        ),
    ]
