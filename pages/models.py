from django.db import models

class Page(models.Model):
    text = models.TextField()
    title = models.CharField(max_length=500)
    path = models.CharField(max_length=255)
    template = models.CharField(max_length=255)
    
    blobs = models.ManyToManyField('Blob', blank=True)

    class Meta:
        verbose_name = 'Content'
        verbose_name_plural = 'Page content'

    def __str__(self):
        return self.title

class Blob(models.Model):
    text = models.TextField()
    context_name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Chunk'
        verbose_name_plural = 'Content chunks'
    
    def __str__(self):
        return self.context_name
