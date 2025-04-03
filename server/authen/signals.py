from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from rest_framework.authtoken.models import Token
from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Create a token automatically when a new user is created.
    This ensures every user always has a token.
    """
    if created:
        Token.objects.create(user=instance)
