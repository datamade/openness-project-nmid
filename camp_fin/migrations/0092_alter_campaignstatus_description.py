# Generated by Django 3.2.25 on 2024-06-01 12:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0091_auto_20240529_0738"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campaignstatus",
            name="description",
            field=models.CharField(max_length=100),
        ),
    ]
