# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-31 15:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0023_remove_transaction_candidate"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidate",
            name="slug",
            field=models.CharField(default=" ", max_length=500),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="pac",
            name="slug",
            field=models.CharField(default=" ", max_length=500),
            preserve_default=False,
        ),
    ]
