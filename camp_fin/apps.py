from django.apps import AppConfig


class CampFinConfig(AppConfig):
    name = 'camp_fin'
    verbose_name = 'Campaign Finance'

    def ready(self):
        # Import signal handlers
        import camp_fin.signals
