# Generated by Django 3.2.25 on 2024-05-02 13:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0088_auto_20240425_1018"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="campaign",
            name="committee_address",
        ),
        migrations.RemoveField(
            model_name="campaign",
            name="committee_email",
        ),
        migrations.RemoveField(
            model_name="campaign",
            name="committee_fax_number",
        ),
        migrations.RemoveField(
            model_name="campaign",
            name="committee_name",
        ),
        migrations.RemoveField(
            model_name="campaign",
            name="committee_phone_1",
        ),
        migrations.RemoveField(
            model_name="campaign",
            name="committee_phone_2",
        ),
        migrations.AddField(
            model_name="campaign",
            name="committee",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="campaigns",
                to="camp_fin.pac",
            ),
            preserve_default=False,
        ),
    ]
