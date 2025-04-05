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

# Import room finding views
from .room_finders import (
    FindDirectRoomView,
    FindGroupRoomsView,
    FindRoomByNameView,
    UserRoomsView,
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
    # Room finding endpoints
    path("find-direct-room/", FindDirectRoomView.as_view(), name="find-direct-room"),
    path("find-group-rooms/", FindGroupRoomsView.as_view(), name="find-group-rooms"),
    path("find-room-by-name/", FindRoomByNameView.as_view(), name="find-room-by-name"),
    path("my-rooms/", UserRoomsView.as_view(), name="my-rooms"),
]
