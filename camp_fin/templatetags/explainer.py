from django import template
from django.conf import settings
from django.utils.translation import get_language
from django.utils.translation import ugettext_lazy as _

register = template.Library()

@register.inclusion_tag('camp_fin/widgets/explainer.html')
def explainer(text=''):
    '''
    Create a help widget to explain a piece of text.
    '''
    context = {}

    context['explainer_text'] = text

    return context
