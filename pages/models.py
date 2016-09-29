from django.db import models

class Page(models.Model):
    text = models.TextField()
    title = models.CharField(max_length=500)
    path = models.CharField(max_length=255)
    template = models.CharField(max_length=255)

    def __str__(self):
        return self.title

class Blob(models.Model):
    text = models.TextField()
    page = models.ForeignKey('Page')
    context_name = models.CharField(max_length=20)

    def __str__(self):
        return '{0} {1}'.format(self.page.title, 
                                self.context_name.title)
