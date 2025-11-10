from django.apps import AppConfig


class UserappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "userApp"
    verbose_name = "Users"

    def ready(self):
        try:
            from . import signals
        except Exception:
            pass