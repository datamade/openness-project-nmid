# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-17 15:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="candidate",
            name="business_phone",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="first_name",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="home_phone",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="last_name",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="candidate",
            name="middle_name",
            field=models.CharField(max_length=50, null=True),
        ),
    ]
