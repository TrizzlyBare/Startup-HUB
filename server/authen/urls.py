from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from .views import (
    # ViewSet
    AuthViewSet,
    ContactLinkViewSet,
    PublicContactLinksView,
    # Authentication Views
    RegisterView,
    LoginView,
    LogoutView,
    # Profile Views
    ProfileView,
    ProfileDetailView,
    PublicProfileView,
    # Password Management
    PasswordChangeView,
    # Token Views
    GetTokenView,
    # Career Summary
    CareerSummaryView,
    UserContactLinksAPIView,
    # User Search
    UserSearchView,
    # Debug Views
    AuthDebugView,
    token_debug,
    UserContactLinksView,
)

# Create a schema view for API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Authentication & Profile API",
        default_version="v1",
        description="API documentation for user management, authentication, and professional profiles",
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
# Add the contact links router here BEFORE using it in urlpatterns
router.register(r"contact-links", ContactLinkViewSet, basename="contact-links")

# URL patterns
urlpatterns = [
    # Router URLs
    path("", include(router.urls)),
    # Authentication Endpoints
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Profile Endpoints
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/<str:username>/", ProfileView.as_view(), name="profile-username"),
    path("profiles/", ProfileDetailView.as_view(), name="profile-list"),
    # Public Profile Endpoint
    path(
        "public-profile/<str:username>/",
        PublicProfileView.as_view(),
        name="public-profile",
    ),
    # User Search Endpoint
    path("users/search/", UserSearchView.as_view(), name="user-search"),
    # Career Summary Endpoint
    path("career-summary/", CareerSummaryView.as_view(), name="career-summary"),
    # Password Management
    path("change-password/", PasswordChangeView.as_view(), name="change-password"),
    # Token Endpoints
    path("token/", GetTokenView.as_view(), name="get-token"),
    path("token-debug/", token_debug, name="token-debug"),
    # Auth Debug Endpoint
    path("auth-debug/", AuthDebugView.as_view(), name="auth-debug"),
    # API Documentation
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
    # Public contact links for a specific user - add it here in the main urlpatterns
    path(
        "contact-links/username/<str:username>/",
        ContactLinkViewSet.as_view({"get": "retrieve_by_username"}),
        name="contact-links-by-username",
    ),
    # Public contact links with explicit path
    path(
        "public-contact-links/<str:username>/",
        PublicContactLinksView.as_view(),
        name="public-contact-links",
    ),
    path(
        "contact-links/<str:username>/",
        UserContactLinksAPIView.as_view(),
        name="user-contact-links",
    ),
]
