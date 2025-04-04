from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, MessageViewSet, MediaFileViewSet

router = DefaultRouter()
router.register(r"rooms", RoomViewSet)
router.register(r"messages", MessageViewSet)
router.register(r"media", MediaFileViewSet)

# Get view functions from viewsets
room_detail = RoomViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)

room_send_message = RoomViewSet.as_view({"post": "send_message"})

room_message_list = MessageViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

urlpatterns = [
    path("", include(router.urls)),
    # Add explicit paths that match what the client is expecting
    path("rooms/<uuid:pk>/", room_detail, name="room-detail"),
    path("rooms/<uuid:pk>/send_message/", room_send_message, name="room-send-message"),
    # Our previous fix for room messages
    path("rooms/<uuid:room_id>/messages/", room_message_list, name="room-messages"),
]
