from django.urls import re_path
from . import consumers
from . import webrtc

websocket_urlpatterns = [
    # Username-based WebSocket route
    re_path(
        r"ws/communication/(?P<username>[\w-]+)/$",
        consumers.CommunicationConsumer.as_asgi(),
        name="direct_chat",
    ),
    # Existing room-based route
    re_path(
        r"ws/room/(?P<room_id>[0-9a-f-]+)/$",
        consumers.CommunicationConsumer.as_asgi(),
        name="room_communication",
    ),
    # WebRTC signaling (unchanged)
    re_path(
        r"ws/webrtc/(?P<room_id>[0-9a-f-]+)/$",
        webrtc.WebRTCSignalingConsumer.as_asgi(),
    ),
]
