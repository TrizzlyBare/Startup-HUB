from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RoomViewSet,
    MessageViewSet,
    MediaFileViewSet,
    DirectRoomView,
    RoomMessagesView,
    UsernameLoginView,
)

router = DefaultRouter()
router.register(r"rooms", RoomViewSet, basename="room")
router.register(r"messages", MessageViewSet, basename="message")
router.register(r"media", MediaFileViewSet, basename="media")

urlpatterns = [
    path("", include(router.urls)),
    # Authentication endpoint
    path("login/", UsernameLoginView.as_view(), name="username-login"),
    # Direct route for creating a direct message room between users
    path("room/direct/", DirectRoomView.as_view(), name="direct-room"),
    # Specific route for room messages with UUID validation
    path(
        "rooms/<uuid:room_id>/messages/",
        RoomMessagesView.as_view(),
        name="room-messages",
    ),
]
