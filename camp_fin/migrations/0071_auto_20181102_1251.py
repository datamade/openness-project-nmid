# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-11-02 18:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0070_auto_20180920_1242_squashed_0073_auto_20180920_1248"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lobbyistreport",
            name="pdf_report",
            field=models.CharField(max_length=50, null=True),
        ),
    ]
