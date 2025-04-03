from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, MessageViewSet, MediaFileViewSet

router = DefaultRouter()
router.register(r"rooms", RoomViewSet)
router.register(r"messages", MessageViewSet)
router.register(r"media", MediaFileViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
