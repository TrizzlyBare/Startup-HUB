from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from rest_framework.authtoken.models import Token
import re


class BearerTokenAuthMiddleware(MiddlewareMixin):
    """
    Middleware to handle both 'Bearer token' and 'Token token' authentication formats
    in headers and extract tokens from query parameters if needed.
    """

    def process_request(self, request):
        # Skip authentication for paths that don't need it
        if any(
            re.match(pattern, request.path)
            for pattern in [
                r"^/admin/",
                r"^/api/auth/register/",
                r"^/api/auth/login/",
                r"^/api/register/",
                r"^/api/login/",
                r"^/swagger/",
                r"^/redoc/",
            ]
        ):
            return None

        # Check Authorization header first (both Bearer and Token formats)
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if auth_header.startswith("Bearer "):
            token_key = auth_header.split(" ")[1]
        elif auth_header.startswith("Token "):
            token_key = auth_header.split(" ")[1]
        # Check for token query parameter as fallback
        elif request.GET.get("token"):
            token_key = request.GET.get("token")
        else:
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
