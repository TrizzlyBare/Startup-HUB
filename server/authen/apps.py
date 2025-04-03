from django.apps import AppConfig


class AuthenConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "authen"

    def ready(self):
        """
        Import signals when the app is ready.
        This ensures the signal handlers are registered.
        """
        import authen.signals
