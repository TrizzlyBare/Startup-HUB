from rest_framework.authentication import TokenAuthentication as BaseTokenAuthentication
from rest_framework import exceptions
from rest_framework.authtoken.models import Token
from django.utils.translation import gettext_lazy as _


class BearerTokenAuthentication(BaseTokenAuthentication):
    """
    Custom token authentication that supports 'Bearer' prefix in addition to 'Token'.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth:
            return None

        # Try to authenticate with both 'Bearer' and 'Token' keywords
        auth_parts = auth.split()

        if len(auth_parts) != 2:
            return None

        if auth_parts[0] not in ["Bearer", "Token"]:
            return None

        token = auth_parts[1]

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, key):
        try:
            token = Token.objects.get(key=key)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        return (token.user, token)
