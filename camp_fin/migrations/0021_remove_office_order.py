# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-29 21:22
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0020_auto_20160829_1519"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="office",
            name="order",
        ),
    ]
