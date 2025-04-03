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
                r"^/api/register/",
                r"^/api/login/",
                r"^/swagger/",
                r"^/redoc/",
                r"^/api/auth-debug/",  # Skip for auth debugging
            ]
        ):
            return None

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
