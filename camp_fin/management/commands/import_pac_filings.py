import logging

from django.core.management.base import BaseCommand

from camp_fin import models

from .import_filing import Command as FilingCommand
from .utils import parse_date

logger = logging.getLogger(__name__)


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
            # MemberID isn't stable across separate CFIS data pulls, so it
            # can't be used to join this filings file back to the PAC
            # committees file. Name is the only field the two files share
            # reliably. It isn't always unique, so warn when a name maps to
            # more than one PAC -- those need manual review -- but proceed
            # with the most recently added match rather than skip the
            # filing outright.
            pacs = models.PAC.objects.filter(name=record["CommitteeName"])

            if not pacs.exists():
                logger.warning(
                    f"No PAC named '{record['CommitteeName']}' exists. "
                    f"Skipping filing record: {record}"
                )
                return

            if pacs.count() > 1:
                logger.warning(
                    f"{pacs.count()} PACs named '{record['CommitteeName']}' "
                    "exist and this filing has no state ID to disambiguate "
                    "them. Using the most recently added PAC. Manual "
                    "review recommended."
                )

            entity = pacs.order_by("date_added").last().entity

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
