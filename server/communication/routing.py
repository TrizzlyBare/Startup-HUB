from django.urls import re_path
from . import consumers
from . import webrtc

websocket_urlpatterns = [
    # Use only the consumer classes that are actually defined
    re_path(
        r"ws/communication/(?P<room_id>[0-9a-f-]+)/$",
        consumers.CommunicationConsumer.as_asgi(),
    ),
    # WebRTC signaling (unchanged)
    re_path(
        r"ws/webrtc/(?P<room_id>[0-9a-f-]+)/$",
        webrtc.WebRTCSignalingConsumer.as_asgi(),
    ),
]
