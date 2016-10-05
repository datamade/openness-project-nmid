from django.test import TestCase
from django.urls import reverse

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
