#!/bin/bash
set -euo pipefail

python manage.py createcachetable 
python manage.py migrate --noinput

if [ `psql ${DATABASE_URL} -tAX -c "SELECT COUNT(*) FROM camp_fin_candidate"` -eq "0" ]; then
    python manage.py import_data
    python -W ignore manage.py import_data_2023 --source-file _data/raw/CON_2020.csv
    python -W ignore manage.py import_data_2023 --source-file _data/raw/CON_2021.csv
    python -W ignore manage.py import_data_2023 --source-file _data/raw/CON_2022.csv
    python -W ignore manage.py import_data_2023 --source-file _data/raw/CON_2023.csv
    python manage.py make_search_index
fi

python manage.py clear_cache
