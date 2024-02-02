import functools

from django.db.models.query import QuerySet


def cache_func(func):
    @functools.wraps(func)
    @functools.lru_cache(maxsize=1024)
    def with_cache(self, *args, **kwargs):
        return func(self, *args, **kwargs)

    return with_cache


def hash_qs(self):
    return hash(self.model)


def eq_qs(self, other):
    return self.model == other.model


def cache_patch():
    QuerySet.get = cache_func(QuerySet.get)
    QuerySet.__hash__ = hash_qs
    QuerySet.__eq__ = eq_qs
