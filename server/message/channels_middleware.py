# channels_middleware.py

import functools
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from urllib.parse import parse_qs
from django.conf import settings


@database_sync_to_async
def get_user_from_token(token_key):
    """Get user from token"""
    try:
        token = Token.objects.get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware:
    """
    Custom middleware that takes a token from the query string and authenticates via Django REST Framework.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Get query parameters
        query_params = parse_qs(scope["query_string"].decode())
        token_key = query_params.get("token", [None])[0]

        if token_key:
            # Get the user from the token
            scope["user"] = await get_user_from_token(token_key)
        else:
            scope["user"] = AnonymousUser()

        # Return the inner application
        return await self.app(scope, receive, send)


def TokenAuthMiddlewareStack(inner):
    """Wrapper function for the token auth middleware"""
    return TokenAuthMiddleware(inner)
