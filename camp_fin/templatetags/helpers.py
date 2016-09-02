from django.template import Library

register = Library()

@register.filter()
def format_money(s):
    import locale
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    return locale.currency(s, grouping=True)

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
