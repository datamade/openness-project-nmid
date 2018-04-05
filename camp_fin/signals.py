from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.management import call_command

@receiver([post_save, post_delete])
def clear_cache_on_update(sender, **kwargs):
    '''
    Clear the cache after any model has been saved or deleted.
    '''
    call_command('clear_cache')
