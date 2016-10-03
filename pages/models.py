from django.db import models
from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver


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

@receiver(post_save, sender=Page)
def clear_cache(sender, **kwargs):
    cache.clear()

class Blob(models.Model):
    text = models.TextField()
    context_name = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Chunk'
        verbose_name_plural = 'Content chunks'
    
    def __str__(self):
        return self.context_name
