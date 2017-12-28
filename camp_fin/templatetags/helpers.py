from django.template import Library

register = Library()

@register.filter()
def format_money(s):
    import locale
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    if s:
        s = float(s)
        return locale.currency(s, grouping=True)
    return '$0.00'

@register.filter()
def format_money_short(n):
    if not n:
        return '$0'
    import math
    millnames=['','K','M','B']
    n = float(n)
    millidx=max(0,min(len(millnames)-1,
                      int(math.floor(math.log10(abs(n))/3))))
    return '$%.1f%s'%(n/10**(3*millidx),millnames[millidx])

@register.simple_tag
def query_transform(request, **kwargs):
    updated = request.GET.copy()
    for k,v in kwargs.items():
        updated[k] = v
    return updated.urlencode()

@register.filter
def get_sort_icon(s):
    if s.lower() == 'desc':
        return ' <i class="fa fa-sort-amount-desc"> </i>'
    return ' <i class="fa fa-sort-amount-asc"> </i>'

@register.filter
def get_transaction_verb(s):
    verbs = {
        'Monetary contribution': 'donated',
        'In Kind contribution': 'donated in-kind',
        'Anonymous Contribution': 'anonymously donated',
        'Refund monetary  (NOT BEING USED)': 'was refunded',
        'Monetary Expenditure': 'spent',
    }
    return verbs.get(s, '')

@register.simple_tag
def funds_raised(campaign, year, short=False):
    '''
    Retrives the amount of funds raised for a candidate in a given year.
    '''
    funds = campaign.funds_raised(since=year)

    if short:
        output = format_money_short(funds)
    else:
        output = format_money(funds)

    return output

@register.simple_tag
def expenditures(campaign, year, short=False):
    '''
    Retrives the expenditures for a candidate in a given year.
    '''
    expenditures = campaign.expenditures(since=year)

    if short:
        output = format_money_short(expenditures)
    else:
        output = format_money(expenditures)

    return output

@register.filter
def total_funds(races):
    '''
    Return the total amount of funds raised in a set of races.
    '''
    return sum(race.total_funds for race in races)

@register.filter
def percentage(obj, total):
    '''
    Return a campaign's share (percentage) of the total funds raised in a given
    context.
    '''
    return obj.share_of_funds(total)
