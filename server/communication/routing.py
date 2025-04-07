from django.urls import re_path
from . import webrtc
from .chat_consumer import ChatConsumer  # Import our unified consumer
from .webrtc_consumer import WebRTCSignalingConsumer


websocket_urlpatterns = [
    # Username-based WebSocket route
    re_path(
        r"ws/communication/(?P<username>[\w-]+)/$",
        ChatConsumer.as_asgi(),
        name="direct_chat",
    ),
    # Room-based WebSocket route
    re_path(
        r"ws/room/(?P<room_id>[0-9a-f-]+)/$",
        ChatConsumer.as_asgi(),
        name="room_communication",
    ),
    # # WebRTC signaling (unchanged)
    # re_path(
    #     r"ws/webrtc/(?P<room_id>[0-9a-f-]+)/$",
    #     webrtc.WebRTCSignalingConsumer.as_asgi(),
    # ),
    re_path(
        r"ws/webrtc/(?P<room_id>[0-9a-f-]+)/$",
        WebRTCSignalingConsumer.as_asgi(),
    ),
]
