"""
ASGI config for server project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import message.routing
import webcall.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                message.routing.websocket_urlpatterns
                + webcall.routing.websocket_urlpatterns
            )
        ),
    }
)


ASGI_APPLICATION = "server.asgi.application"
