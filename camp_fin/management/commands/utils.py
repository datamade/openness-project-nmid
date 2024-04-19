import re

from dateutil.parser import ParserError, parse
from dateutil.tz import gettz


def convert_to_float(value):
    value = re.sub("[^0-9.]", "", value)
    if value.startswith("("):
        return -float(value)
    else:
        return float(value)


def parse_date(date_str):
    try:
        mountain_tz = gettz("America/Denver")
        return parse(date_str).replace(tzinfo=mountain_tz)
    except (ParserError, TypeError):
        return None
