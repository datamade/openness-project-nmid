# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-08 15:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0039_auto_20160908_0936"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contact",
            name="full_name",
            field=models.CharField(max_length=500, null=True),
        ),
    ]
