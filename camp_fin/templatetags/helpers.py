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
def largest_contribution(races):
    '''
    Return the largest amount of funds raised in single race among a set of races.
    '''
    return max(race.largest_contribution for race in races)

@register.filter
def percentage(obj, total):
    '''
    Return a campaign's share (percentage) of the total funds raised in a given
    context.
    '''
    return obj.share_of_funds(total)

@register.filter
def format_years(years):
    '''
    Return a nicely formatted string from a list of years. For continuous years,
    display a range; for disjoint years, return a comma-separated list.
    '''
    def get_ranges(current, future, final):
        '''
        Given a list of years, return a list of lists corresponding to the years
        spanned, with continuous ranges represented by nested lists.
        e.g. `[2012, 2013, 2015]` will return `[[2012, 2013], [2015]]`.
        '''
        # Base case
        if len(future) == 0:
            final.append(current)
            return final

        curr_year, next_year = current[-1], future.pop(0)

        if int(curr_year) + 1 == int(next_year):
            # Continuous years -- extend the current list
            current.append(next_year)
        elif curr_year == next_year:
            # Duplicate -- skip this one
            pass
        else:
            # Disjoint years -- append the current list to the output, and restart it
            final.append(current)
            current = [next_year]

        return get_ranges(current, future, final)

    def format_range(rng):
        '''
        Given a list of years, return a string representing the range of years
        spanned. e.g. `[2012, 2013, 2014]` will return `2012-2014`.
        '''
        if len(rng) == 0:
            return ''
        elif len(rng) == 1:
            return rng[0]
        else:
            start, end = rng[0], rng[-1]
            return "{start} - {end}".format(start=start, end=end)

    if len(years) == 0:
        return ''
    elif len(years) == 1:
        return str(years[0])
    else:
        sorted_years = sorted(years)
        ranges = get_ranges([sorted_years[0]], sorted_years[1:], [])
        return ', '.join(format_range(rng) for rng in ranges)

@register.simple_tag
def lobbyist_contributions(obj, employer_id, short=False):
    '''
    Return the total amount of political contributions by a lobbyist working
    under a given employer.
    '''
    funds = obj.total_contributions(employer_id=employer_id)

    if short:
        output = format_money_short(funds)
    else:
        output = format_money(funds)

    return output

@register.simple_tag
def lobbyist_expenditures(obj, employer_id, short=False):
    '''
    Return the total amount of expenditures by a lobbyist working under a
    given employer.
    '''
    funds = obj.total_expenditures(employer_id=employer_id)

    if short:
        output = format_money_short(funds)
    else:
        output = format_money(funds)

    return output
