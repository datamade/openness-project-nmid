# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-02-13 22:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0062_race_dropouts"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="race",
            name="dropouts",
        ),
        migrations.AddField(
            model_name="campaign",
            name="race_status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("dropout", "Dropped out"),
                    ("lost_primary", "Lost primary"),
                ],
                default="active",
                max_length=25,
            ),
        ),
    ]
