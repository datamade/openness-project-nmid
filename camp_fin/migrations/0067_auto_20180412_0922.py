# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-04-12 15:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0066_auto_20180412_0854"),
    ]

    operations = [
        migrations.AlterField(
            model_name="candidate",
            name="deceased",
            field=models.CharField(max_length=3, null=True),
        ),
    ]
