# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-30 18:45
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0022_remove_officetype_order"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="transaction",
            name="candidate",
        ),
    ]
