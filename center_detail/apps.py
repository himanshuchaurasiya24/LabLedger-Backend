from django.apps import AppConfig


class CenterDetailConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'center_detail'
    def ready(self):
        import center_detail.signals
