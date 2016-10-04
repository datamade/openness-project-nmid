from django.conf import settings
from django.db import connection

def last_updated(request):
    cursor = connection.cursor()

    cursor.execute(''' 
        SELECT 
          MAX(received_date) AS last_updated 
        FROM camp_fin_transaction 
        WHERE received_date BETWEEN (NOW() - INTERVAL '1 year') AND now()
    ''')

    last_updated = cursor.fetchone()[0]

    return {'LAST_UPDATED': last_updated}

def seo_context(request):

    return {'SITE_META': settings.SITE_META}
