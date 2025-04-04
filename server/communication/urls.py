from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, MessageViewSet, MediaFileViewSet

router = DefaultRouter()
router.register(r"rooms", RoomViewSet)
router.register(r"messages", MessageViewSet)
router.register(r"media", MediaFileViewSet)

# Create nested routes for room messages
room_message_list = MessageViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

urlpatterns = [
    path("", include(router.urls)),
    # Add explicit path for room messages (both GET and POST)
    path("rooms/<uuid:room_id>/messages/", room_message_list, name="room-messages"),
    # Alternative method using RoomViewSet actions
    # path("rooms/<uuid:pk>/messages/", RoomViewSet.as_view({
    #     'get': 'messages',
    #     'post': 'send_message'
    # }), name="room-messages"),
]
