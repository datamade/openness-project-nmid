# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2023-12-12 17:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0076_auto_20231130_1404"),
    ]

    operations = [
        migrations.AlterField(
            model_name="entitytype",
            name="description",
            field=models.CharField(max_length=256),
        ),
    ]
