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
    import math
    millnames=['','K','M','B']
    n = float(n)
    millidx=max(0,min(len(millnames)-1,
                      int(math.floor(math.log10(abs(n))/3))))
    return '$%.2f%s'%(n/10**(3*millidx),millnames[millidx])

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

