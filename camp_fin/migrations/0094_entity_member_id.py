from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("camp_fin", "0093_auto_20250121_0716"),
    ]

    operations = [
        migrations.AddField(
            model_name="entity",
            name="member_id",
            field=models.CharField(max_length=255, null=True),
        ),
    ]
