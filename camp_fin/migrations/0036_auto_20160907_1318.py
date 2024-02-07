# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-07 19:18
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0035_auto_20160906_1505"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidate",
            name="full_name",
            field=models.CharField(default="", max_length=500),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="loan",
            name="full_name",
            field=models.CharField(default="", max_length=500),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transaction",
            name="full_name",
            field=models.CharField(default="", max_length=500),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="treasurer",
            name="full_name",
            field=models.CharField(default="", max_length=500),
            preserve_default=False,
        ),
    ]
