# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-01-08 17:42
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0058_auto_20180108_1031"),
    ]

    operations = [
        migrations.AddField(
            model_name="campaign",
            name="note",
            field=models.TextField(blank=True, null=True),
        ),
    ]
