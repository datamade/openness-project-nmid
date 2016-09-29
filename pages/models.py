from django.db import models

class Page(models.Model):
    text = models.TextField()
    title = models.CharField(max_length=500)
    path = models.CharField(max_length=255)
    template = models.CharField(max_length=255)
    
    blobs = models.ManyToManyField('Blob')

    def __str__(self):
        return self.title

class Blob(models.Model):
    text = models.TextField()
    context_name = models.CharField(max_length=20)

    def __str__(self):
        return self.context_name
