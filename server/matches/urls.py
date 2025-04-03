from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MatchViewSet, LikeViewSet, DislikeViewSet, PotentialMatchesView

# Create router for ViewSet routes
match_router = DefaultRouter()
match_router.register(r"matches", MatchViewSet, basename="match")
match_router.register(r"likes", LikeViewSet, basename="like")
match_router.register(r"dislikes", DislikeViewSet, basename="dislike")

# URL patterns for matching functionality
urlpatterns = [
    # ViewSet routes
    path("", include(match_router.urls)),
    # Get potential matches
    path(
        "potential-matches/", PotentialMatchesView.as_view(), name="potential-matches"
    ),
]
