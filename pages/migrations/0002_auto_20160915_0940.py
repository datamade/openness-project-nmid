# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-15 15:40
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="page",
            old_name="slug",
            new_name="path",
        ),
    ]
