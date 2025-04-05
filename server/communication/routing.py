from django.urls import re_path
from . import consumers
from . import webrtc

websocket_urlpatterns = [
    # Primary room-based WebSocket route for all communications
    re_path(
        r"ws/room/(?P<room_id>[0-9a-f-]+)/$",
        consumers.CommunicationConsumer.as_asgi(),
        name="room_communication",
    ),
    # WebRTC signaling
    re_path(
        r"ws/webrtc/(?P<room_id>[0-9a-f-]+)/$",
        webrtc.WebRTCSignalingConsumer.as_asgi(),
    ),
]
