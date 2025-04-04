from django.apps import AppConfig
import os


class CommunicationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "communication"

    def ready(self):
        # Only configure Cloudinary in the main process, not in management commands

        if os.environ.get("RUN_MAIN", None) != "true":
            from .utils.cloudinary_helper import CloudinaryHelper

            CloudinaryHelper.configure()
