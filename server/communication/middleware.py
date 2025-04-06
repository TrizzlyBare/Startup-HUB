from django.utils.deprecation import MiddlewareMixin
import cloudinary
from django.conf import settings
import logging
import hmac
from django.utils.crypto import constant_time_compare


# Set up logging
logger = logging.getLogger(__name__)


class CloudinaryConfigMiddleware(MiddlewareMixin):
    """
    Middleware to ensure Cloudinary is configured for every request
    """

    def process_request(self, request):
        try:
            # Check if Cloudinary is already configured
            if (
                not hasattr(cloudinary.config(), "cloud_name")
                or not cloudinary.config().cloud_name
            ):
                cloudinary.config(
                    cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
                    api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
                    api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
                )
                logger.debug("Cloudinary configured in middleware")
        except Exception as e:
            logger.error(f"Failed to configure Cloudinary in middleware: {str(e)}")
        return None


class WebSocketAuthMiddleware:
    """
    Authentication middleware for WebSocket connections with timing attack protection
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Check if the connection is a websocket
        if scope["type"] == "websocket":
            # Get the user from the scope
            user = scope.get("user", None)

            # Use constant_time_compare to prevent timing attacks
            is_authenticated = user is not None and constant_time_compare(
                str(getattr(user, "is_authenticated", False)), "True"
            )

            # If no user is authenticated, close the connection
            if not is_authenticated:
                await send(
                    {
                        "type": "websocket.close",
                        "code": 4003,  # Custom code for authentication failure
                    }
                )
                return

        # If authenticated or not a websocket, continue with the connection
        return await self.app(scope, receive, send)


from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from authen.authentication import BearerTokenAuthentication
import logging

logger = logging.getLogger(__name__)


class WebSocketTokenAuthMiddleware:
    """
    WebSocket middleware that authenticates using the same flexible token
    mechanism as the REST API.
    """

    def __init__(self, app):
        self.app = app
        self.bearer_auth = BearerTokenAuthentication()

    async def __call__(self, scope, receive, send):
        # Add user to scope
        scope["user"] = await self.get_user(scope)

        # Continue with next middleware or application
        return await self.app(scope, receive, send)

    async def get_user(self, scope):
        """
        Get user from query string token or header using the existing BearerTokenAuthentication
        """
        # Check if user is already authenticated
        if scope.get("user", None) and scope["user"].is_authenticated:
            return scope["user"]

        # Build a request-like object that our BearerTokenAuthentication can use
        request = WebSocketRequestAdapter(scope)

        # Use the existing authentication class to authenticate
        try:
            auth_result = await database_sync_to_async(self.bearer_auth.authenticate)(
                request
            )
            if auth_result:
                user, token = auth_result
                return user
        except Exception as e:
            logger.error(f"Error authenticating WebSocket: {str(e)}")

        # Return anonymous user if no valid token found
        return AnonymousUser()


class WebSocketRequestAdapter:
    """
    Adapter to make WebSocket scope look like a Django request for authentication
    """

    def __init__(self, scope):
        self.scope = scope
        self.META = {}
        self.GET = {}

        # Extract headers from WebSocket scope
        for name, value in scope.get("headers", []):
            name = name.decode("utf-8").upper().replace("-", "_")
            value = value.decode("utf-8")
            self.META[f"HTTP_{name}"] = value

        # Extract query string parameters
        query_string = scope.get("query_string", b"").decode("utf-8")
        if query_string:
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    self.GET[key] = value
