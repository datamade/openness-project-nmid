from django.test import TestCase, override_settings
from django.urls import reverse

TEST_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_nmid',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

@override_settings(DATABASES=TEST_DATABASES)
class TestViews(TestCase):
    def test_index(self):
        response = self.client.get(reverse('index'))
        assert response.status_code == 200

    def test_about(self):
        response = self.client.get(reverse('about'))
        assert response.status_code == 200

    def test_donations(self):
        response = self.client.get(reverse('donations'))
        assert response.status_code == 200
