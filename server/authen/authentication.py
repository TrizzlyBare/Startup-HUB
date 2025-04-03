from rest_framework.authentication import TokenAuthentication as BaseTokenAuthentication
from rest_framework import exceptions
from rest_framework.authtoken.models import Token
from django.utils.translation import gettext_lazy as _


class BearerTokenAuthentication(BaseTokenAuthentication):
    """
    Custom token authentication that supports more flexible token formats.
    Accepts: 'Bearer <token>', 'Token <token>', '<token>' or token in query params.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth:
            # Try to get from query params as fallback
            token_param = request.GET.get("token")
            if token_param:
                return self.authenticate_credentials(token_param)
            return None

        # Handle various formats more flexibly
        auth = auth.strip()  # Remove any whitespace

        # Case 1: Just the token with no prefix
        if " " not in auth:
            return self.authenticate_credentials(auth)

        # Case 2: Standard prefixed tokens
        parts = auth.split(" ", 1)  # Split only on first space
        prefix, token = parts

        if prefix not in ["Bearer", "Token"]:
            # Try using the whole string as token (in case it contains spaces)
            return self.authenticate_credentials(auth)

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key):
        try:
            token = Token.objects.get(key=key)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        return (token.user, token)
