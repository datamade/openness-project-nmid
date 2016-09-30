from django.conf import settings

def seo_context(request):

    return {'SITE_META': settings.SITE_META}
