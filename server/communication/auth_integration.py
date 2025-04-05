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
        # Check for authentication token in headers
        headers = dict(scope.get("headers", []))
        token_key = headers.get(b"authorization", b"").decode().replace("Token ", "")

        user = None
        if token_key:
            user = await self.get_user_by_token(token_key)

        # If no valid token, user remains unauthenticated
        if not user:
            scope["user"] = AnonymousUser()
        else:
            scope["user"] = user

        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user_by_token(self, token_key):
        try:
            token = Token.objects.select_related("user").get(key=token_key)
            if token.user.is_active:
                return token.user
        except Token.DoesNotExist:
            logger.warning(f"Invalid token: {token_key}")
        return None
