#!/bin/sh
set -e

if [ "$DJANGO_MANAGEPY_MIGRATE" = 'on' ]; then
    python manage.py migrate --noinput
fi

if [ "$DJANGO_CACHE_BACKEND" = 'db.DatabaseCache' ]; then
    python manage.py createcachetable
fi

exec "$@"
