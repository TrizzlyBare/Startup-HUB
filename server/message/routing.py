from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_id>[0-9a-f-]+)/$", consumers.ChatConsumer.as_asgi()),
    re_path(r"ws/echo/$", consumers.EchoConsumer.as_asgi()),
]
