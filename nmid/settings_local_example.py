# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'super secret key'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nmid',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': 'nmid_cache',
    }
}

FLUSH_CACHE_KEY = 'something secret'

# This is an optional directory where the import data process will check for
# files before looking in the "data" directory within the project.
FTP_DIRECTORY = ''
