# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-30 15:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0005_auto_20160930_0851"),
    ]

    operations = [
        migrations.AlterField(
            model_name="page",
            name="blobs",
            field=models.ManyToManyField(blank=True, to="pages.Blob"),
        ),
    ]
