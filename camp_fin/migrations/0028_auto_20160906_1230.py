# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-09-06 18:30
from __future__ import unicode_literals

import datetime

import django.db.models.deletion
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ("camp_fin", "0027_auto_20160906_0757"),
    ]

    operations = [
        migrations.CreateModel(
            name="EntityType",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("description", models.CharField(max_length=25)),
            ],
        ),
        migrations.CreateModel(
            name="Loan",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date_added", models.DateTimeField()),
                ("amount", models.FloatField()),
                ("check_number", models.CharField(max_length=30, null=True)),
                ("memo", models.CharField(max_length=500, null=True)),
                ("received_date", models.DateTimeField()),
                ("interest_rate", models.FloatField(null=True)),
                ("due_date", models.DateTimeField(null=True)),
                ("payment_schedule_id", models.IntegerField(null=True)),
                ("oldb_id", models.IntegerField(null=True)),
                ("name_prefix", models.CharField(max_length=25, null=True)),
                ("first_name", models.CharField(max_length=255, null=True)),
                ("middle_name", models.CharField(max_length=255, null=True)),
                ("last_name", models.CharField(max_length=255, null=True)),
                ("suffix", models.CharField(max_length=15, null=True)),
                ("company_name", models.CharField(max_length=255, null=True)),
                ("address", models.CharField(max_length=255, null=True)),
                ("city", models.CharField(max_length=50, null=True)),
                ("state", models.CharField(max_length=25, null=True)),
                ("zipcode", models.CharField(max_length=10, null=True)),
                ("country", models.CharField(max_length=50, null=True)),
                ("contact_type_other", models.CharField(max_length=25, null=True)),
                ("occupation", models.CharField(max_length=255, null=True)),
                ("loan_transfer_date", models.DateTimeField(null=True)),
                ("from_file_id", models.IntegerField(null=True)),
                (
                    "contact",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="camp_fin.Contact",
                    ),
                ),
                (
                    "contact_type",
                    models.ForeignKey(
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="camp_fin.ContactType",
                    ),
                ),
                (
                    "county",
                    models.ForeignKey(
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="camp_fin.County",
                    ),
                ),
                (
                    "filing",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="camp_fin.Filing",
                    ),
                ),
                (
                    "status",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="camp_fin.Status",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="LoanTransaction",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.FloatField()),
                ("interest_paid", models.FloatField(null=True)),
                ("transaction_date", models.DateTimeField()),
                ("date_added", models.DateTimeField()),
                ("check_number", models.CharField(max_length=10, null=True)),
                ("memo", models.CharField(max_length=500, null=True)),
                ("from_file_id", models.IntegerField(null=True)),
                (
                    "filing",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="camp_fin.Filing",
                    ),
                ),
                (
                    "loan",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="camp_fin.Loan",
                    ),
                ),
                (
                    "transaction_status",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="camp_fin.Status",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="LoanTransactionType",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("description", models.CharField(max_length=25)),
            ],
        ),
        migrations.CreateModel(
            name="SpecialEvent",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("event_name", models.CharField(max_length=255, null=True)),
                ("date_added", models.DateTimeField()),
                ("event_date", models.DateField()),
                ("admission_price", models.FloatField()),
                ("attendance", models.IntegerField()),
                ("location", models.CharField(max_length=255, null=True)),
                ("description", models.TextField()),
                ("sponsors", models.TextField()),
                ("total_admissions", models.FloatField()),
                ("anonymous_contributions", models.FloatField()),
                ("total_expenditures", models.FloatField()),
                ("olddb_id", models.IntegerField(null=True)),
                ("address", models.CharField(max_length=255, null=True)),
                ("city", models.CharField(max_length=100, null=True)),
                ("zipcode", models.CharField(max_length=10, null=True)),
                ("country", models.CharField(max_length=50, null=True)),
                ("from_file_id", models.IntegerField(null=True)),
                (
                    "county",
                    models.ForeignKey(
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="camp_fin.County",
                    ),
                ),
                (
                    "filing",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="camp_fin.Filing",
                    ),
                ),
                (
                    "transaction_status",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="camp_fin.Status",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="division",
            name="district",
            field=models.ForeignKey(
                db_constraint=False,
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="camp_fin.District",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="division",
            name="name",
            field=models.CharField(default="", max_length=25),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="division",
            name="status",
            field=models.ForeignKey(
                db_constraint=False,
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="camp_fin.Status",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="electionseason",
            name="special",
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="electionseason",
            name="status",
            field=models.ForeignKey(
                db_constraint=False,
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="camp_fin.Status",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="electionseason",
            name="year",
            field=models.CharField(default=1000, max_length=5),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="entity",
            name="olddb_id",
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name="entity",
            name="user_id",
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name="filingtype",
            name="description",
            field=models.CharField(default="", max_length=25),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="politicalparty",
            name="name",
            field=models.CharField(default="", max_length=25),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="treasurer",
            name="address",
            field=models.ForeignKey(
                db_constraint=False,
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="camp_fin.Address",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="treasurer",
            name="alt_phone",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="treasurer",
            name="business_phone",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="treasurer",
            name="date_added",
            field=models.DateTimeField(
                default=datetime.datetime(2016, 9, 6, 18, 30, 51, 47411, tzinfo=utc)
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="treasurer",
            name="email",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="treasurer",
            name="first_name",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="treasurer",
            name="last_name",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="treasurer",
            name="middle_name",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="treasurer",
            name="olddb_entity_id",
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name="treasurer",
            name="prefix",
            field=models.CharField(max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="treasurer",
            name="status",
            field=models.ForeignKey(
                db_constraint=False,
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="camp_fin.Status",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="treasurer",
            name="suffix",
            field=models.CharField(max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name="district",
            name="status",
            field=models.ForeignKey(
                db_constraint=False,
                on_delete=django.db.models.deletion.CASCADE,
                to="camp_fin.Status",
            ),
        ),
        migrations.AddField(
            model_name="loantransaction",
            name="transaction_type",
            field=models.ForeignKey(
                db_constraint=False,
                on_delete=django.db.models.deletion.CASCADE,
                to="camp_fin.LoanTransactionType",
            ),
        ),
        migrations.AddField(
            model_name="entity",
            name="entity_type",
            field=models.ForeignKey(
                db_constraint=False,
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="camp_fin.EntityType",
            ),
            preserve_default=False,
        ),
    ]
