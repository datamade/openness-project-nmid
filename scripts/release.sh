#!/bin/bash
set -euo pipefail

python manage.py createcachetable
python manage.py migrate --noinput

if [ `psql ${DATABASE_URL} -tAX -c "SELECT COUNT(*) FROM camp_fin_candidate"` -eq "0" ]; then
    make nightly
    python manage.py make_search_index
fi

if [ `psql ${DATABASE_URL} -tAX -c "SELECT COUNT(*) FROM pages_page"` -eq "0" ]; then
    python manage.py loaddata pages/fixtures/static_pages.json
fi

python manage.py clear_cache
