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
