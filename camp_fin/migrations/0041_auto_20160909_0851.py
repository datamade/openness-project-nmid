# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-09 14:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0040_auto_20160908_0937"),
    ]

    operations = [
        migrations.AlterField(
            model_name="treasurer",
            name="full_name",
            field=models.CharField(max_length=500, null=True),
        ),
    ]
