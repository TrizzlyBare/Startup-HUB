"""
ASGI config for server project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

# asgi.py
import os
import django
from django.core.asgi import get_asgi_application

# Set up Django BEFORE importing routing modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
django.setup()

# Now import routing modules
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import message.routing
import webcall.routing
import communication.routing

# Initialize Django ASGI application
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            # URLRouter(
            #     message.routing.websocket_urlpatterns
            #     + webcall.routing.websocket_urlpatterns
            # )
            URLRouter(communication.routing.websocket_urlpatterns)
        ),
    }
)

ASGI_APPLICATION = "server.asgi.application"

# """
# ASGI configuration for project.

# It exposes the ASGI callable as a module-level variable named ``application``.

# For more information on this file, see
# https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
# """

# import os
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.security.websocket import AllowedHostsOriginValidator

# # Import the auth middleware
# from communication.middleware import WebSocketTokenAuthMiddleware

# # Import the routing configuration
# import communication.routing

# # Set Django settings module
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

# # Initialize Django ASGI application
# django_asgi_app = get_asgi_application()

# # Configure the ASGI application
# application = ProtocolTypeRouter(
#     {
#         # Django's built-in ASGI application handler for HTTP
#         "http": django_asgi_app,
#         # WebSocket handler with authentication and allowed hosts validation
#         "websocket": AllowedHostsOriginValidator(
#             WebSocketTokenAuthMiddleware(
#                 URLRouter(communication.routing.websocket_urlpatterns)
#             )
#         ),
#     }
# )
