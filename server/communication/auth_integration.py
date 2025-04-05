# communication/auth_integration.py

from rest_framework.authtoken.models import Token
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
import logging
import base64

User = get_user_model()
logger = logging.getLogger(__name__)


class CommunicationAuthMiddleware:
    """
    Custom authentication middleware for the communication WebSocket
    that integrates with your existing token authentication system.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Try to authenticate the user
        user = await self.get_user(scope)
        scope["user"] = user

        # If user is not authenticated, close the connection
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await send(
                {
                    "type": "websocket.close",
                    "code": 4003,  # Authentication failure
                }
            )
            return

        # Continue with the connection
        return await self.app(scope, receive, send)

    async def get_user(self, scope):
        """
        Try multiple auth methods:
        1. Token in query string
        2. Bearer token in headers
        3. Basic auth in headers
        4. Username in headers
        """
        # Try to authenticate using query string
        query_string = scope.get("query_string", b"").decode("utf-8")
        if query_string:
            query_params = dict(
                param.split("=") for param in query_string.split("&") if param
            )
            if "token" in query_params:
                token = query_params["token"]
                user = await self.get_user_from_token(token)
                if user:
                    return user

            if "username" in query_params:
                username = query_params["username"]
                return await self.get_user_by_username(username)

        # Try to authenticate using headers
        headers = dict(scope.get("headers", []))

        # Look for Authorization header (Bearer/Token)
        auth_header = headers.get(b"authorization", b"")
        if auth_header:
            auth_header = auth_header.decode("utf-8")

            # Handle Bearer token
            if auth_header.startswith("Bearer ") or auth_header.startswith("Token "):
                token = auth_header.split(" ", 1)[1]
                user = await self.get_user_from_token(token)
                if user:
                    return user

            # Handle Basic auth
            elif auth_header.startswith("Basic "):
                try:
                    auth_data = base64.b64decode(auth_header[6:]).decode("utf-8")
                    username, _ = auth_data.split(":", 1)
                    return await self.get_user_by_username(username)
                except Exception as e:
                    logger.error(f"Error decoding basic auth: {str(e)}")

            # Try using the whole header as token
            elif " " not in auth_header:
                user = await self.get_user_from_token(auth_header)
                if user:
                    return user

        # Look for username header
        username_header = headers.get(b"username", b"")
        if username_header:
            username = username_header.decode("utf-8")
            return await self.get_user_by_username(username)

        # No valid authentication found
        return AnonymousUser()

    @database_sync_to_async
    def get_user_from_token(self, token):
        """
        Get a user from a token key
        """
        try:
            token_obj = Token.objects.get(key=token)
            if token_obj.user.is_active:
                return token_obj.user
        except Token.DoesNotExist:
            logger.warning(f"Invalid token: {token}")
        return None

    @database_sync_to_async
    def get_user_by_username(self, username):
        """
        Get a user by username
        """
        try:
            user = User.objects.get(username=username)
            if user.is_active:
                return user
        except User.DoesNotExist:
            logger.warning(f"User not found: {username}")
        return None
