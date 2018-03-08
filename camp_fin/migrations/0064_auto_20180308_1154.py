# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-03-08 18:54
from __future__ import unicode_literals

import camp_fin.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('camp_fin', '0063_auto_20180213_1541'),
    ]

    operations = [
        migrations.CreateModel(
            name='Lobbyist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_added', models.DateTimeField(null=True)),
                ('prefix', models.CharField(max_length=10, null=True)),
                ('first_name', models.CharField(max_length=50, null=True)),
                ('middle_name', models.CharField(max_length=50, null=True)),
                ('last_name', models.CharField(max_length=50, null=True)),
                ('suffix', models.CharField(max_length=10, null=True)),
                ('email', models.CharField(max_length=100, null=True)),
                ('registration_date', models.DateTimeField(null=True)),
                ('termination_date', models.DateTimeField(null=True)),
                ('phone', models.CharField(max_length=30, null=True)),
                ('date_updated', models.DateTimeField(null=True)),
                ('slug', models.CharField(max_length=500, null=True)),
                ('contact', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Contact')),
                ('entity', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Entity')),
            ],
            bases=(models.Model, camp_fin.models.LobbyistMethodMixin),
        ),
        migrations.CreateModel(
            name='LobbyistBundlingDisclosure',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('destinatary_name', models.CharField(max_length=100)),
                ('date_added', models.DateTimeField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='LobbyistBundlingDisclosureContributor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('amount', models.FloatField()),
                ('occupation', models.CharField(max_length=250, null=True)),
                ('address', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='lobbyist_bundling_disclosure_contributor_address', to='camp_fin.Address')),
                ('bundling_disclosure', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistBundlingDisclosure')),
            ],
        ),
        migrations.CreateModel(
            name='LobbyistEmployer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_added', models.DateTimeField(null=True)),
                ('year', models.CharField(max_length=5)),
                ('lobbyist', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Lobbyist')),
            ],
        ),
        migrations.CreateModel(
            name='LobbyistFilingPeriod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filing_date', models.DateTimeField(null=True)),
                ('due_date', models.DateTimeField(null=True)),
                ('description', models.CharField(max_length=100)),
                ('allow_statement_of_no_activity', models.NullBooleanField()),
                ('initial_date', models.DateTimeField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='LobbyistFilingPeriodType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='LobbyistRegistration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_added', models.DateTimeField(null=True)),
                ('year', models.CharField(max_length=5)),
                ('is_registered', models.NullBooleanField()),
                ('lobbyist', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Lobbyist')),
            ],
        ),
        migrations.CreateModel(
            name='LobbyistReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_added', models.DateTimeField(null=True)),
                ('date_closed', models.DateTimeField(null=True)),
                ('date_updated', models.DateTimeField(null=True)),
                ('pdf_report', models.CharField(max_length=50)),
                ('meal_beverage_expenses', models.FloatField()),
                ('entertainment_expenses', models.FloatField()),
                ('gift_expenses', models.FloatField()),
                ('other_expenses', models.FloatField()),
                ('special_event_expenses', models.FloatField()),
                ('expenditures', models.FloatField()),
                ('political_contributions', models.FloatField()),
                ('entity', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Entity')),
                ('lobbyist_filing_period', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistFilingPeriod')),
                ('status', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Status')),
            ],
        ),
        migrations.CreateModel(
            name='LobbyistSpecialEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(max_length=100)),
                ('location', models.CharField(max_length=100)),
                ('received_date', models.DateTimeField(null=True)),
                ('amount', models.FloatField()),
                ('groups_invited', models.CharField(max_length=2000, null=True)),
                ('date_added', models.DateTimeField(null=True)),
                ('lobbyist_report', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistReport')),
            ],
        ),
        migrations.CreateModel(
            name='LobbyistTransaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, null=True)),
                ('beneficiary', models.CharField(max_length=250, null=True)),
                ('expenditure_purpose', models.CharField(max_length=250, null=True)),
                ('received_date', models.DateTimeField(null=True)),
                ('amount', models.FloatField()),
                ('date_added', models.DateTimeField(null=True)),
                ('lobbyist_report', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistReport')),
            ],
        ),
        migrations.CreateModel(
            name='LobbyistTransactionGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='LobbyistTransactionStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='LobbyistTransactionType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=100)),
                ('group', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistTransactionGroup')),
            ],
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_added', models.DateTimeField(null=True)),
                ('name', models.CharField(max_length=100)),
                ('email', models.CharField(max_length=100, null=True)),
                ('date_updated', models.DateTimeField(null=True)),
                ('phone', models.CharField(max_length=30, null=True)),
                ('slug', models.CharField(max_length=500, null=True)),
                ('contact', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Contact')),
                ('entity', models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Entity')),
                ('permanent_address', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='organization_permanent_address', to='camp_fin.Address')),
                ('status', models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Status')),
            ],
            bases=(models.Model, camp_fin.models.LobbyistMethodMixin),
        ),
        migrations.AddField(
            model_name='lobbyisttransaction',
            name='lobbyist_transaction_type',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistTransactionType'),
        ),
        migrations.AddField(
            model_name='lobbyisttransaction',
            name='transaction_status',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistTransactionStatus'),
        ),
        migrations.AddField(
            model_name='lobbyistspecialevent',
            name='transaction_status',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistTransactionStatus'),
        ),
        migrations.AddField(
            model_name='lobbyistfilingperiod',
            name='lobbyist_filing_period_type',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistFilingPeriodType'),
        ),
        migrations.AddField(
            model_name='lobbyistfilingperiod',
            name='regular_filing_period',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.FilingPeriod'),
        ),
        migrations.AddField(
            model_name='lobbyistemployer',
            name='organization',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Organization'),
        ),
        migrations.AddField(
            model_name='lobbyistbundlingdisclosurecontributor',
            name='lobbyist_report',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistReport'),
        ),
        migrations.AddField(
            model_name='lobbyistbundlingdisclosure',
            name='lobbyist_report',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistReport'),
        ),
        migrations.AddField(
            model_name='lobbyistbundlingdisclosure',
            name='transaction_status',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistTransactionStatus'),
        ),
        migrations.AddField(
            model_name='lobbyist',
            name='filing_period',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.LobbyistFilingPeriod'),
        ),
        migrations.AddField(
            model_name='lobbyist',
            name='lobbying_address',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='lobbyist_lobbying_address', to='camp_fin.Address'),
        ),
        migrations.AddField(
            model_name='lobbyist',
            name='permanent_address',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='lobbyist_permanent_address', to='camp_fin.Address'),
        ),
        migrations.AddField(
            model_name='lobbyist',
            name='status',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='camp_fin.Status'),
        ),
    ]
