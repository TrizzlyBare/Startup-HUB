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
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from communication.routing import websocket_urlpatterns
from communication.auth_integration import CommunicationAuthMiddleware

# Initialize Django ASGI application
django_asgi_app = get_asgi_application()

# application = ProtocolTypeRouter(
#     {
#         "http": django_asgi_app,
#         "websocket": AuthMiddlewareStack(
#             URLRouter(communication.routing.websocket_urlpatterns)
#         ),
#     }
# )

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": CommunicationAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)

ASGI_APPLICATION = "server.asgi.application"
