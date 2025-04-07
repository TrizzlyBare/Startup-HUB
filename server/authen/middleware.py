from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from rest_framework.authtoken.models import Token
import re


class BearerTokenAuthMiddleware(MiddlewareMixin):
    """
    Middleware to handle multiple token authentication formats
    in headers and extract tokens from query parameters.
    """

    def process_request(self, request):
        # Skip authentication for paths that don't need it
        if any(
            re.match(pattern, request.path)
            for pattern in [
                r"^/admin/",
                r"^/api/auth/register/",
                r"^/api/auth/login/",
                r"^/api/auth/token/$",  # Original token endpoint
                r"^/api/auth/token/[^/]+/?$",  # New token endpoint with username
                r"^/api/register/",
                r"^/api/login/",
                r"^/swagger/",
                r"^/redoc/",
                r"^/api/auth-debug/",  # Skip for auth debugging
            ]
        ):
            return None

        # Rest of the middleware implementation...

        # Rest of your middleware code...

        # Check Authorization header first (various formats)
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        token_key = None

        if auth_header:
            auth_parts = auth_header.split()
            if len(auth_parts) == 1:
                # Just the token
                token_key = auth_parts[0]
            elif len(auth_parts) == 2 and auth_parts[0] in ["Bearer", "Token"]:
                # Bearer or Token prefix
                token_key = auth_parts[1]

        # Check for token query parameter as fallback
        if not token_key and request.GET.get("token"):
            token_key = request.GET.get("token")

        if not token_key:
            # No token found, continue with view's permission checks
            return None

        try:
            token = Token.objects.get(key=token_key)
            # Add authenticated user to request
            request.user = token.user
        except Token.DoesNotExist:
            # Token not found but let the view handle authentication failure
            pass

        return None


from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from django.utils.deprecation import MiddlewareMixin


class WebSocketTokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Add user to scope
        scope["user"] = await self.get_user(scope)

        # Continue with next middleware or application
        return await self.app(scope, receive, send)

    async def get_user(self, scope):
        # Extract token from query string or headers
        query_string = scope.get("query_string", b"").decode()
        headers = dict(scope.get("headers", []))

        token_key = None
        if "token" in query_string:
            token_key = query_string.split("=")[-1]

        auth_header = headers.get(b"authorization", b"").decode()
        if auth_header.startswith("Bearer "):
            token_key = auth_header.split(" ")[1]

        if token_key:
            try:
                token = await database_sync_to_async(Token.objects.get)(key=token_key)
                return token.user
            except Token.DoesNotExist:
                pass

        return AnonymousUser()
