from rest_framework.authtoken.models import Token
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class CommunicationAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Extract username from route
        username = scope["url_route"]["kwargs"].get("username")

        # Find user by username if provided
        if username:
            user = await self.get_user_by_username(username)

            # Ensure user is authenticated
            if not user or not user.is_authenticated:
                await send(
                    {"type": "websocket.close", "code": 4003}  # Authentication failure
                )
                return

            # Modify scope to include authenticated user
            scope["user"] = user

        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user_by_username(self, username):
        try:
            user = User.objects.get(username=username)
            # Optional: Add additional authentication checks
            if user.is_active:
                return user
        except User.DoesNotExist:
            logger.warning(f"User not found: {username}")
        return None
