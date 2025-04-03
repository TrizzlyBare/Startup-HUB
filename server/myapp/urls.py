from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StartupIdeaViewSet

router = DefaultRouter()
router.register(r"startup-ideas", StartupIdeaViewSet, basename="startup-idea")

urlpatterns = [
    path("", include(router.urls)),
]
