# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-09 21:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0044_auto_20160909_1116"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="amount",
            field=models.FloatField(db_index=True),
        ),
    ]
