# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-08 15:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('camp_fin', '0038_contact_occupation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='date_added',
            field=models.DateTimeField(null=True),
        ),
    ]