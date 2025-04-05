from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, MessageViewSet, MediaFileViewSet

router = DefaultRouter()
router.register(r"rooms", RoomViewSet, basename="room")
router.register(r"messages", MessageViewSet, basename="message")
router.register(r"media", MediaFileViewSet, basename="media")

urlpatterns = [
    path("", include(router.urls)),
    # Specific route for room messages
    path(
        "rooms/<uuid:room_id>/messages/",
        RoomViewSet.as_view({"get": "messages"}),
        name="room-messages",
    ),
]
