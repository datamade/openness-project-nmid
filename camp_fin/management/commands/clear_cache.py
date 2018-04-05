from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """
    A simple management command which clears the site-wide cache.

    Code adapted from Randall Degges:
    https://github.com/rdegges/django-clear-cache
    """

    help = 'Fully clear your site-wide cache.'

    def handle(self, *args, **kwargs):
        try:
            assert settings.CACHES
            cache.clear()
        except AttributeError:
            raise CommandError('You have no cache configured!\n')
