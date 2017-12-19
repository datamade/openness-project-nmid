# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-12-11 22:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('camp_fin', '0055_auto_20170412_0927'),
    ]

    operations = [
        migrations.CreateModel(
            name='Race',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('district', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.District')),
                ('division', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Division')),
                ('election_season', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.ElectionSeason')),
            ],
        ),
        migrations.CreateModel(
            name='RaceGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('short_title', models.CharField(max_length=50)),
                ('full_title', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=250)),
            ],
        ),
        migrations.AddField(
            model_name='race',
            name='group',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.RaceGroup'),
        ),
        migrations.AddField(
            model_name='race',
            name='office',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Office'),
        ),
        migrations.AddField(
            model_name='race',
            name='office_type',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.OfficeType'),
        ),
        migrations.AddField(
            model_name='race',
            name='winner',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Campaign'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='active_race',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Race'),
        ),
        migrations.AlterUniqueTogether(
            name='race',
            unique_together=set([('district', 'division', 'office_type', 'office', 'election_season')]),
        ),
    ]
