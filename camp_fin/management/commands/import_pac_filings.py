from django.core.management.base import BaseCommand

from camp_fin import models

from .import_filing import Command as FilingCommand
from .utils import parse_date


class Command(FilingCommand, BaseCommand):
    def _create_filing(self, record):

        filing_type, _ = models.FilingType.objects.get_or_create(
            description=record["ReportName"][:24]
        )

        filing_period, _ = models.FilingPeriod.objects.get_or_create(
            description=record["ReportName"],
            initial_date=parse_date(record["FilingStartDate"]),
            end_date=parse_date(record["FilingEndDate"]),
            due_date=parse_date(record["FilingDueDate"]),
            allow_no_activity=False,
            exclude_from_cascading=False,
            email_sent_status=0,
            filing_period_type=filing_type,
        )

        state_id = record["StateID"]
        if state_id:
            entity = models.Entity.objects.get(user_id=state_id)

        else:
            entity = models.PAC.objects.get(name=record["CommitteeName"]).entity

        url = f"https://login.cfis.sos.state.nm.us//ReportsOutput//{record['ReportFileName']}"
        final = record["Amended"] == "0" or None

        filing = models.Filing.objects.create(
            filing_period=filing_period,
            filed_date=parse_date(record["FilingEndDate"]),
            date_closed=parse_date(record["FilingEndDate"]),
            entity=entity,
            final=final,
            pdf_report=url or None,
            report_id=record["ReportID"],
            report_version_id=record["ReportVersionID"],
        )

        return filing
