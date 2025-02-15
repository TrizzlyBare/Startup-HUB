from django.urls import path, include
from rest_framework_nested import routers
from . import views

# Create main router
router = routers.DefaultRouter()
router.register(r"rooms", views.RoomViewSet, basename="room")

# Create nested router for room-specific endpoints
rooms_router = routers.NestedDefaultRouter(router, r"rooms", lookup="room")
rooms_router.register(r"messages", views.MessageViewSet, basename="room-messages")
rooms_router.register(
    r"participants", views.ParticipantViewSet, basename="room-participants"
)

app_name = "chat"

urlpatterns = [
    path("", include(router.urls)),
    path("", include(rooms_router.urls)),
]
