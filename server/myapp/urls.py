from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StartupIdeaViewSet

router = DefaultRouter()
router.register(r"startup-ideas", StartupIdeaViewSet, basename="startup-idea")

urlpatterns = [
    path("", include(router.urls)),
]  # Add these to your existing StartupIdea URLs
urlpatterns += [
    path(
        "startup-ideas/<pk>/request-to-join/",
        StartupIdeaViewSet.as_view({"post": "request_to_join"}),
        name="request-to-join",
    ),
    path(
        "startup-ideas/my-join-requests/",
        StartupIdeaViewSet.as_view({"get": "my_join_requests"}),
        name="my-join-requests",
    ),
    path(
        "startup-ideas/pending-join-requests/",
        StartupIdeaViewSet.as_view({"get": "pending_join_requests"}),
        name="pending-join-requests",
    ),
    # Add this to your urls.py file in the urlpatterns list
    path(
        "startup-ideas/<pk>/join-request/<request_id>/",
        StartupIdeaViewSet.as_view(
            {
                "put": "handle_join_request",
                "patch": "handle_join_request",
                "delete": "delete_join_request",
            }
        ),
        name="delete-join-request",
    ),
    path(
        "startup-ideas/<pk>/project-join-requests/",
        StartupIdeaViewSet.as_view({"get": "project_join_requests"}),
        name="project-join-requests",
    ),
]

# The routes generated include:

# GET /startup-ideas/ - List all startup ideas
# POST /startup-ideas/ - Create a new startup idea
# GET /startup-ideas/{id}/ - Get details of a startup idea
# PUT/PATCH /startup-ideas/{id}/ - Update a startup idea
# DELETE /startup-ideas/{id}/ - Delete a startup idea

# Custom actions:
# GET /startup-ideas/all-projects/ - Get all accessible projects with pagination and filtering
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
# GET /startup-ideas/{id}/project-join-requests/ - Get all join requests for a specific project
