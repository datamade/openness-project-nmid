from django.db import models

class Page(models.Model):
    text = models.TextField()
    title = models.CharField(max_length=500)
    path = models.CharField(max_length=255)
    template = models.CharField(max_length=255)

    def __str__(self):
        return self.title
