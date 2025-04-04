from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StartupIdeaViewSet

router = DefaultRouter()
router.register(r"startup-ideas", StartupIdeaViewSet, basename="startup-idea")

urlpatterns = [
    path("", include(router.urls)),
]

# The routes generated include:

# GET /startup-ideas/ - List all startup ideas
# POST /startup-ideas/ - Create a new startup idea
# GET /startup-ideas/{id}/ - Get details of a startup idea
# PUT/PATCH /startup-ideas/{id}/ - Update a startup idea
# DELETE /startup-ideas/{id}/ - Delete a startup idea

# Custom actions:
# GET /startup-ideas/my-ideas/ - Get ideas owned by a user (takes username as query parameter)
# GET /startup-ideas/user-ideas/ - Get ideas owned by current user or specified username (via query param)
# GET /startup-ideas/my-memberships/ - Get ideas where current user is a member (but not owner)
# GET /startup-ideas/search/ - Search startup ideas
# GET /startup-ideas/match-suggestions/ - Get ideas matching user's skills/industry
# GET /startup-ideas/{id}/members/ - Get all members of a startup idea
# POST /startup-ideas/{id}/add-member/ - Add a member to a startup idea
# POST /startup-ideas/{id}/remove-member/ - Remove a member from a startup idea
# POST /startup-ideas/{id}/join-startup/ - Join a startup as a member
# POST /startup-ideas/{id}/leave-startup/ - Leave a startup
# POST /startup-ideas/{id}/upload-image/ - Upload an image for a startup
# POST /startup-ideas/{id}/upload-pitch-deck/ - Upload a pitch deck
# DELETE /startup-ideas/{id}/remove-image/ - Remove an image
