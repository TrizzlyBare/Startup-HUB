from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
import cloudinary
from django.contrib.auth import get_user_model

from .models import JoinRequest, StartupIdea, StartupImage
from .serializers import (
    JoinRequestSerializer,
    StartupIdeaSerializer,
    StartupImageSerializer,
    UserBasicSerializer,
)

from .email_utils import send_join_request_notification

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count
from django.contrib.auth import get_user_model

from .models import StartupIdea
from .serializers import StartupIdeaSerializer

User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API results"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


# Custom permission class to restrict access
class IsOwnerOrMemberOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners, members or admins to access an idea.
    """

    def has_object_permission(self, request, view, obj):
        # Admin permissions
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Check if user is the owner
        if obj.user == request.user:
            return True

        # Check if user is a member
        if obj.members.filter(id=request.user.id).exists():
            return True

        # Deny access otherwise
        return False


class StartupIdeaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing startup ideas.
    Users can create multiple startup ideas, update, and delete their own ideas.
    """

    serializer_class = StartupIdeaSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # Added JSONParser
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "updated_at", "name", "stage"]
    ordering = ["-created_at"]  # Default ordering

    def get_permissions(self):
        """
        Apply different permissions based on the action:
        - List/Create: Basic authenticated user
        - Retrieve/Update/Delete: Owner, member or admin
        """
        if self.action in ["retrieve", "update", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, IsOwnerOrMemberOrAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Return ideas the user can access - their own or ones they're a member of"""
        user = self.request.user

        # Admin can see all
        if user.is_staff or user.is_superuser:
            return StartupIdea.objects.all()

        # Regular users can only see their own ideas or those they're a member of
        return StartupIdea.objects.filter(Q(user=user) | Q(members=user)).distinct()

    def perform_create(self, serializer):
        """Associate the new idea with the current user"""
        startup = serializer.save(user=self.request.user)
        # Automatically add the owner as a member if needed
        startup.members.add(self.request.user)

    def perform_update(self, serializer):
        """Ensure users can only update their own ideas"""
        startup_idea = self.get_object()
        if startup_idea.user != self.request.user:
            raise PermissionDenied(
                "You don't have permission to edit this startup idea"
            )
        serializer.save()

    def perform_destroy(self, instance):
        """Ensure users can only delete their own ideas"""
        if instance.user != self.request.user:
            raise PermissionDenied(
                "You don't have permission to delete this startup idea"
            )
        instance.delete()

    @action(detail=False, methods=["get"], url_path="my-ideas")
    def my_ideas(self, request):
        """
        Get startup ideas by username from query parameter.
        URL pattern: /api/startup-profile/startup-ideas/my-ideas/?username=value
        If no username is provided, returns the current user's ideas.
        """
        username = request.query_params.get("username")

        # Check if the user is admin
        is_admin = request.user.is_staff or request.user.is_superuser

        if username:
            try:
                target_user = User.objects.get(username=username)

                # Security check: only allow viewing others' ideas if:
                # 1. You are the target user (viewing your own)
                # 2. You are an admin
                # 3. You are a member of the ideas
                if request.user.username != username and not is_admin:
                    # Only get ideas where the current user is a member
                    ideas = StartupIdea.objects.filter(
                        user=target_user, members=request.user
                    ).distinct()
                else:
                    # Get all ideas for the target user (admin or self access)
                    ideas = StartupIdea.objects.filter(user=target_user)

            except User.DoesNotExist:
                return Response(
                    {"error": f"User '{username}' not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # If no username provided, default to current user's ideas
            ideas = StartupIdea.objects.filter(user=request.user)

        # Apply additional filters
        stage = request.query_params.get("stage", None)
        if stage:
            ideas = ideas.filter(stage=stage)

        funding_stage = request.query_params.get("funding_stage", None)
        if funding_stage:
            ideas = ideas.filter(funding_stage=funding_stage)

        # Order by creation date (newest first)
        ideas = ideas.order_by("-created_at")

        serializer = self.get_serializer(ideas, many=True)
        return Response({"count": ideas.count(), "results": serializer.data})

    @action(detail=True, methods=["post"])
    def upload_image(self, request, pk=None):
        """Upload an image for a specific startup idea"""
        idea = self.get_object()

        # Check if user has permission to add images to this idea
        if idea.user != request.user:
            return Response(
                {"error": "You do not have permission to add images to this idea"},
                status=status.HTTP_403_FORBIDDEN,
            )

        image = request.FILES.get("image")
        caption = request.data.get("caption", "")

        if not image:
            return Response(
                {"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        startup_image = StartupImage.objects.create(
            startup_idea=idea, image=image, caption=caption
        )

        return Response(
            StartupImageSerializer(startup_image).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def upload_pitch_deck(self, request, pk=None):
        """Upload a pitch deck for a specific startup idea"""
        idea = self.get_object()

        # Check if user has permission to update this idea
        if idea.user != request.user:
            return Response(
                {"error": "You do not have permission to update this idea"},
                status=status.HTTP_403_FORBIDDEN,
            )

        pitch_deck = request.FILES.get("pitch_deck")

        if not pitch_deck:
            return Response(
                {"error": "No pitch deck provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        idea.pitch_deck = pitch_deck
        idea.save()

        return Response(StartupIdeaSerializer(idea).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="user-ideas")
    def user_ideas(self, request):
        """
        Get all startup ideas for a specific user by username.
        If no username is provided, returns the current user's ideas.
        This method maintains security restrictions like my_ideas.
        """
        username = request.query_params.get("username")

        # Check if the user is admin
        is_admin = request.user.is_staff or request.user.is_superuser

        if username:
            try:
                target_user = User.objects.get(username=username)

                # Security check: only allow viewing others' ideas if:
                # 1. You are the target user (viewing your own)
                # 2. You are an admin
                # 3. You are a member of the ideas
                if request.user.username != username and not is_admin:
                    # Only get ideas where the current user is a member
                    ideas = StartupIdea.objects.filter(
                        user=target_user, members=request.user
                    ).distinct()
                else:
                    # Get all ideas for the target user (admin or self access)
                    ideas = StartupIdea.objects.filter(user=target_user)

            except User.DoesNotExist:
                return Response(
                    {"error": f"User '{username}' not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # If no username provided, default to current user's ideas
            ideas = StartupIdea.objects.filter(user=request.user)

        serializer = self.get_serializer(ideas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_memberships(self, request):
        """Get all startup ideas where the current user is a member but not the owner"""
        ideas = StartupIdea.objects.filter(members=request.user).exclude(
            user=request.user
        )
        serializer = self.get_serializer(ideas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """
        Search for startup ideas by various criteria.
        Only returns ideas the user has access to (own or member of).
        """
        stage = request.query_params.get("stage", "")
        user_role = request.query_params.get("user_role", "")
        looking_for = request.query_params.get("looking_for", "")
        skills = request.query_params.get("skills", "")

        # Start with the user's accessible queryset
        queryset = self.get_queryset()

        if stage:
            queryset = queryset.filter(stage=stage)

        if user_role:
            queryset = queryset.filter(user_role=user_role)

        # For text fields, use contains lookup for partial matches
        if looking_for:
            queryset = queryset.filter(looking_for__icontains=looking_for)

        if skills:
            queryset = queryset.filter(skills__icontains=skills)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def match_suggestions(self, request):
        """Get potential matches based on user's skills and industry"""
        # Get the user's skills from their profile
        user = request.user

        # Get all ideas that aren't from the current user
        # Only get ideas the user has access to
        all_ideas = self.get_queryset().exclude(user=user)
        matching_ideas = []

        # If user has skills defined, find ideas looking for those skills
        if user.skills:
            user_skills = [skill.strip().lower() for skill in user.skills.split(",")]

            for idea in all_ideas:
                # Check if any of the user's skills are mentioned in the idea's looking_for
                if any(skill in idea.looking_for.lower() for skill in user_skills):
                    matching_ideas.append(idea.id)
                    continue

        # If user has industry defined, find ideas looking for that industry
        if user.industry:
            industry = user.industry.lower()

            for idea in all_ideas:
                # Only check ideas not already matched by skills
                if (
                    idea.id not in matching_ideas
                    and industry in idea.looking_for.lower()
                ):
                    matching_ideas.append(idea.id)

        # Get the matched ideas as a queryset
        # Only include ideas the user has access to
        matches = self.get_queryset().filter(id__in=matching_ideas)

        serializer = self.get_serializer(matches, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["delete"])
    def remove_image(self, request, pk=None):
        """Remove a specific image from a startup idea"""
        idea = self.get_object()

        if idea.user != request.user:
            return Response(
                {"error": "You do not have permission to remove images from this idea"},
                status=status.HTTP_403_FORBIDDEN,
            )

        image_id = request.data.get("image_id")

        if not image_id:
            return Response(
                {"error": "No image ID provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            image = StartupImage.objects.get(id=image_id, startup_idea=idea)
            image.delete()
            return Response(
                {"message": "Image removed successfully"}, status=status.HTTP_200_OK
            )
        except StartupImage.DoesNotExist:
            return Response(
                {"error": "Image not found"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def add_member(self, request, pk=None):
        """Add a member to the startup idea"""
        idea = self.get_object()

        # Check if user has permission to add members to this idea
        if idea.user != request.user:
            return Response(
                {"error": "You do not have permission to add members to this idea"},
                status=status.HTTP_403_FORBIDDEN,
            )

        username = request.data.get("username")

        if not username:
            return Response(
                {"error": "No username provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(username=username)

            # Check if user is already a member
            if idea.members.filter(id=user.id).exists():
                return Response(
                    {"error": "User is already a member of this startup idea"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add user to members
            idea.members.add(user)

            return Response(
                {"message": f"{username} added as a member successfully"},
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def remove_member(self, request, pk=None):
        """Remove a member from the startup idea"""
        idea = self.get_object()

        # Check if user has permission to remove members from this idea
        if idea.user != request.user:
            return Response(
                {
                    "error": "You do not have permission to remove members from this idea"
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"error": "No user ID provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)

            # Check if user is a member
            if not idea.members.filter(id=user.id).exists():
                return Response(
                    {"error": "User is not a member of this startup idea"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Prevent removing the owner from members
            if user.id == idea.user.id:
                return Response(
                    {"error": "Cannot remove the owner from members"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Remove user from members
            idea.members.remove(user)

            return Response(
                {"message": f"{user.username} removed as a member successfully"},
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """Get all members of a startup idea, including the owner"""
        idea = self.get_object()

        # Get all members
        members = list(idea.members.all())

        # Add the owner if not already in members
        if not idea.members.filter(id=idea.user.id).exists():
            members.append(idea.user)

        serializer = UserBasicSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def join_startup(self, request, pk=None):
        """Allow a user to join a startup idea as a member"""
        idea = self.get_object()

        # Check if user is already a member
        if idea.members.filter(id=request.user.id).exists():
            return Response(
                {"error": "You are already a member of this startup idea"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if user is the owner
        if idea.user.id == request.user.id:
            return Response(
                {"error": "You are the owner of this startup idea"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add user to members
        idea.members.add(request.user)

        return Response(
            {"message": "You have successfully joined this startup idea"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def leave_startup(self, request, pk=None):
        """Allow a user to leave a startup idea"""
        idea = self.get_object()

        # Check if user is the owner
        if idea.user.id == request.user.id:
            return Response(
                {"error": "As the owner, you cannot leave your own startup idea"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if user is a member
        if not idea.members.filter(id=request.user.id).exists():
            return Response(
                {"error": "You are not a member of this startup idea"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remove user from members
        idea.members.remove(request.user)

        return Response(
            {"message": "You have successfully left this startup idea"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="all-projects")
    def all_projects(self, request):
        """
        Get all projects with pagination, filtering and sorting.
        This endpoint shows all projects in the database, regardless of ownership.

        Query Parameters:
        - page: Page number (default: 1)
        - page_size: Number of results per page (default: 10, max: 100)
        - ordering: Sort by field (e.g., 'created_at', '-created_at', 'name')
        - stage: Filter by stage (e.g., 'IDEA', 'MVP', 'EARLY', 'GROWTH', 'SCALING')
        - looking_for: Filter by skills/roles needed (substring match)
        - search: Search in name, pitch and description
        - username: Filter by owner's username
        """
        # Get ALL projects, not just the ones the user has access to
        queryset = StartupIdea.objects.all()

        # Apply filters based on query params
        stage = request.query_params.get("stage")
        if stage:
            queryset = queryset.filter(stage=stage)

        looking_for = request.query_params.get("looking_for")
        if looking_for:
            queryset = queryset.filter(looking_for__icontains=looking_for)

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(pitch__icontains=search)
                | Q(description__icontains=search)
            ).distinct()

        # Filter by owner's username if provided
        username = request.query_params.get("username")
        if username:
            queryset = queryset.filter(user__username=username)

        # Add member count annotation
        queryset = queryset.annotate(member_count_calc=Count("members", distinct=True))

        # Apply ordering (ordering filters are handled by DRF's OrderingFilter)
        ordering = request.query_params.get("ordering")
        if ordering:
            if ordering.startswith("-"):
                queryset = queryset.order_by(ordering)
            else:
                queryset = queryset.order_by(ordering)
        else:
            # Default ordering
            queryset = queryset.order_by("-created_at")

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # If pagination is disabled
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def request_to_join(self, request, pk=None):
        """Request to join a project"""
        startup = self.get_object()

        # Check if user is already a member
        if startup.members.filter(id=request.user.id).exists():
            return Response(
                {"error": "You are already a member of this project"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if user is the owner
        if startup.user == request.user:
            return Response(
                {"error": "You are the owner of this project"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if a request already exists
        existing_request = JoinRequest.objects.filter(
            project=startup, user=request.user, status="pending"
        ).first()

        if existing_request:
            return Response(
                {"error": "You already have a pending request to join this project"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create the join request
        join_request = JoinRequest.objects.create(
            project=startup, user=request.user, message=request.data.get("message", "")
        )

        # Send email notification to the project owner
        send_join_request_notification(join_request)

        serializer = JoinRequestSerializer(join_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def my_join_requests(self, request):
        """Get join requests made by the current user"""
        join_requests = JoinRequest.objects.filter(user=request.user)
        serializer = JoinRequestSerializer(join_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def pending_join_requests(self, request):
        """Get pending join requests for projects owned by the user"""
        join_requests = JoinRequest.objects.filter(
            project__user=request.user, status="pending"
        )
        serializer = JoinRequestSerializer(join_requests, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["put", "patch"],
        url_path="join-request/(?P<request_id>[^/.]+)",
    )
    def handle_join_request(self, request, pk=None, request_id=None):
        """Approve or reject a join request"""
        startup = self.get_object()

        # Check if user is the owner
        if startup.user != request.user:
            return Response(
                {"error": "Only the project owner can handle join requests"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            join_request = JoinRequest.objects.get(id=request_id, project=startup)
        except JoinRequest.DoesNotExist:
            return Response(
                {"error": "Join request not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Update the status
        status_value = request.data.get("status")
        if status_value not in ["approved", "rejected"]:
            return Response(
                {"error": 'Status must be either "approved" or "rejected"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        join_request.status = status_value
        join_request.response_message = request.data.get("response_message", "")
        join_request.save()

        # If approved, add the user as a member
        if status_value == "approved":
            startup.members.add(join_request.user)

        serializer = JoinRequestSerializer(join_request)
        return Response(serializer.data)

    def get_object_for_request_to_join(self):
        """
        Special method to get a project object when a user is requesting to join it.
        This allows accessing projects the user is not yet a member of.
        """
        # Get the pk from the URL
        pk = self.kwargs.get("pk")

        # Try to get the project directly from the database (without ownership restrictions)
        project = get_object_or_404(StartupIdea, pk=pk)
        return project

    @action(detail=True, methods=["get"])
    def project_join_requests(self, request, pk=None):
        """
        Get all join requests for a specific project.

        Returns:
        - project name
        - list of join requests with sender details
        """
        # Get the project
        project = self.get_object()

        # Check if the user is the project owner or an admin
        if project.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "Only the project owner can view join requests"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get all join requests for this project
        join_requests = JoinRequest.objects.filter(project=project)

        # Customize the serialization to include additional details
        request_data = []
        for request in join_requests:
            request_data.append(
                {
                    "id": request.id,
                    "project_name": project.name,
                    "sender_name": request.user.username,
                    "sender_id": request.user.id,
                    "status": request.status,
                    "message": request.message,
                    "created_at": request.created_at,
                }
            )

        return Response(
            {
                "project_name": project.name,
                "project_id": project.id,
                "join_requests": request_data,
            }
        )

    @action(detail=True, methods=["post"])
    def request_to_join(self, request, pk=None):
        """Request to join a project"""
        # Use the special method to get the project
        startup = self.get_object_for_request_to_join()

        # Rest of the method remains the same
        if startup.members.filter(id=request.user.id).exists():
            return Response(
                {"error": "You are already a member of this project"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if startup.user == request.user:
            return Response(
                {"error": "You are the owner of this project"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_request = JoinRequest.objects.filter(
            project=startup, user=request.user, status="pending"
        ).first()

        if existing_request:
            return Response(
                {"error": "You already have a pending request to join this project"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        join_request = JoinRequest.objects.create(
            project=startup, user=request.user, message=request.data.get("message", "")
        )

        # Send email notification to the project owner
        send_join_request_notification(join_request)

        serializer = JoinRequestSerializer(join_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # Add this method to the StartupIdeaViewSet class in views.py

    @action(
        detail=True, methods=["delete"], url_path="join-request/(?P<request_id>[^/.]+)"
    )
    def delete_join_request(self, request, pk=None, request_id=None):
        """
        Delete a specific join request

        Only the request creator or the project owner can delete a join request
        """
        startup = self.get_object()

        try:
            join_request = JoinRequest.objects.get(id=request_id, project=startup)
        except JoinRequest.DoesNotExist:
            return Response(
                {"error": "Join request not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the user is authorized to delete the request
        # Allow if user is either the request creator or the project owner
        if request.user != join_request.user and request.user != startup.user:
            return Response(
                {"error": "You don't have permission to delete this join request"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Log the deletion
        logger.info(
            f"Join request {join_request.id} for project {startup.name} being deleted by {request.user.username}"
        )

        # Delete the join request
        join_request.delete()

        return Response(
            {"message": "Join request deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )
