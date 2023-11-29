# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2023-11-29 17:26
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('camp_fin', '0073_auto_20181102_1259'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 540166, tzinfo=utc), null=True),
        ),
        migrations.AlterField(
            model_name='campaign',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 535579, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 534648, tzinfo=utc), null=True),
        ),
        migrations.AlterField(
            model_name='contact',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 541541, tzinfo=utc), null=True),
        ),
        migrations.AlterField(
            model_name='filing',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 539412, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='loan',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 538089, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='loantransaction',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 538615, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='lobbyist',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 542683, tzinfo=utc), null=True),
        ),
        migrations.AlterField(
            model_name='lobbyistbundlingdisclosure',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 545165, tzinfo=utc), null=True),
        ),
        migrations.AlterField(
            model_name='lobbyistemployer',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 543861, tzinfo=utc), null=True),
        ),
        migrations.AlterField(
            model_name='lobbyistregistration',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 543687, tzinfo=utc), null=True),
        ),
        migrations.AlterField(
            model_name='lobbyistreport',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 544674, tzinfo=utc), null=True),
        ),
        migrations.AlterField(
            model_name='lobbyistspecialevent',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 544959, tzinfo=utc), null=True),
        ),
        migrations.AlterField(
            model_name='lobbyisttransaction',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 544282, tzinfo=utc), null=True),
        ),
        migrations.AlterField(
            model_name='organization',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 543080, tzinfo=utc), null=True),
        ),
        migrations.AlterField(
            model_name='pac',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 535072, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='specialevent',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 538982, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 537413, tzinfo=utc)),
        ),
        migrations.AlterField(
            model_name='treasurer',
            name='date_added',
            field=models.DateTimeField(default=datetime.datetime(2023, 11, 29, 17, 26, 14, 541222, tzinfo=utc)),
        ),
    ]
