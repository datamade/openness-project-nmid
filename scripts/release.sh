#!/bin/bash
set -euo pipefail

python manage.py createcachetable 
python manage.py migrate --noinput

if [ `psql ${DATABASE_URL} -tAX -c "SELECT COUNT(*) FROM camp_fin_candidate"` -eq "0" ]; then
    python manage.py import_data
    make import/offices import/CON_2023 import/EXP_2023
    python manage.py make_search_index
fi

python manage.py clear_cache
