from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from .views import (
    AuthViewSet,
    RegisterView,
    LoginView,
    LogoutView,
    ProfileView,
    PasswordChangeView,
    ProfileDetailView,
)

# Create a schema view for API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Authentication API",
        default_version="v1",
        description="API documentation for authentication and user management endpoints",
        terms_of_service="https://www.yourapp.com/terms/",
        contact=openapi.Contact(email="contact@yourapp.com"),
        license=openapi.License(name="Your License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Create router for ViewSet routes
router = DefaultRouter()
router.register(r"auth", AuthViewSet, basename="auth")

# URL patterns with both ViewSet routes and class-based view routes
urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    # Auth endpoints (no auth required)
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    # Auth endpoints (auth required)
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("change-password/", PasswordChangeView.as_view(), name="change-password"),
    # Profile detail endpoints
    path("profiles/", ProfileDetailView.as_view(), name="profile-detail"),
    path(
        "profiles/<str:username>/",
        ProfileDetailView.as_view(),
        name="profile-detail-username",
    ),
    # Token validation endpoint (useful for frontend)
    path("validate-token/", ProfileView.as_view(), name="validate-token"),
    # API documentation
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]

# Note: Don't add api-auth/ URLs here to avoid namespace collision warning
