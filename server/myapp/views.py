from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
import cloudinary
from django.contrib.auth import get_user_model

from .models import StartupIdea, StartupImage
from .serializers import (
    StartupIdeaSerializer,
    StartupImageSerializer,
    UserBasicSerializer,
)

User = get_user_model()


class StartupIdeaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing startup ideas.
    Users can create multiple startup ideas, update, and delete their own ideas.
    """

    serializer_class = StartupIdeaSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """Return all startup ideas"""
        return StartupIdea.objects.all()

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

    @action(detail=False, methods=["get"])
    def my_ideas(self, request):
        """
        Get all startup ideas for a specific user by username.
        If no username is provided, returns the current user's ideas.
        """
        username = request.query_params.get("username")

        if username:
            user = get_object_or_404(User, username=username)
            ideas = StartupIdea.objects.filter(user=user)
        else:
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
        """Search for startup ideas by various criteria"""
        stage = request.query_params.get("stage", "")
        user_role = request.query_params.get("user_role", "")
        looking_for = request.query_params.get("looking_for", "")
        skills = request.query_params.get("skills", "")

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
        all_ideas = StartupIdea.objects.exclude(user=user)
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
        matches = StartupIdea.objects.filter(id__in=matching_ideas)

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
