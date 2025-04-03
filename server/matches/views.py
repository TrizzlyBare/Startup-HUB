from rest_framework import generics, status, mixins, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django.db.models import Q, Exists, OuterRef
from django.shortcuts import get_object_or_404
from .models import Match, Like, Dislike
from authen.models import CustomUser
from .serializers import (
    MatchSerializer,
    LikeSerializer,
    DislikeSerializer,
    PotentialMatchSerializer,
)


class MatchViewSet(viewsets.ModelViewSet):
    """ViewSet for managing matches"""

    serializer_class = MatchSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return all matches where the current user is either the initiator or recipient"""
        user = self.request.user
        return Match.objects.filter(Q(user=user) | Q(matched_user=user)).order_by(
            "-created_at"
        )

    @action(detail=False, methods=["get"])
    def mutual(self, request):
        """Get only mutual matches"""
        user = request.user
        matches = Match.objects.filter(
            Q(user=user) | Q(matched_user=user), is_mutual=True
        ).order_by("-created_at")
        serializer = self.get_serializer(matches, many=True)
        return Response(serializer.data)


class LikeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing likes (swipe right)"""

    serializer_class = LikeSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Like.objects.filter(user=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        """Process a like (swipe right) and check for a match"""
        # Add the current user to the request data
        data = request.data.copy()
        data["user"] = request.user.id

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            # Save the like
            like = serializer.save(user=request.user)

            # Check if the other person has already liked the current user
            reverse_like_exists = Like.objects.filter(
                user=like.liked_user, liked_user=request.user
            ).exists()

            # If mutual like, create or update the match
            if reverse_like_exists:
                # Check if a match already exists (in either direction)
                match, created = Match.objects.get_or_create(
                    user=request.user,
                    matched_user=like.liked_user,
                    defaults={"is_mutual": True},
                )

                if not created:
                    match.is_mutual = True
                    match.save()

                # Also check for and update a match in the reverse direction
                reverse_match, _ = Match.objects.get_or_create(
                    user=like.liked_user,
                    matched_user=request.user,
                    defaults={"is_mutual": True},
                )

                if not reverse_match.is_mutual:
                    reverse_match.is_mutual = True
                    reverse_match.save()

                return Response(
                    {
                        "like": serializer.data,
                        "match": True,
                        "match_details": MatchSerializer(match).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                # Create a pending match record
                match, _ = Match.objects.get_or_create(
                    user=request.user,
                    matched_user=like.liked_user,
                    defaults={"is_mutual": False},
                )

                return Response(
                    {"like": serializer.data, "match": False},
                    status=status.HTTP_201_CREATED,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DislikeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing dislikes (swipe left)"""

    serializer_class = DislikeSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dislike.objects.filter(user=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        # Add the current user to the request data
        data = request.data.copy()
        data["user"] = request.user.id

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            dislike = serializer.save(user=request.user)

            # Clean up any pending matches
            Match.objects.filter(
                user=request.user, matched_user=dislike.disliked_user, is_mutual=False
            ).delete()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PotentialMatchesView(generics.ListAPIView):
    """View for getting potential matches (users to swipe on)"""

    serializer_class = PotentialMatchSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Exclude users that have already been liked or disliked
        liked_users = Like.objects.filter(user=user, liked_user=OuterRef("pk"))

        disliked_users = Dislike.objects.filter(user=user, disliked_user=OuterRef("pk"))

        # Get potential matches:
        # 1. Not the current user
        # 2. Not already liked/disliked
        potential_matches = CustomUser.objects.exclude(
            Q(pk=user.pk)  # Exclude self
            | Q(Exists(liked_users))  # Exclude already liked
            | Q(Exists(disliked_users))  # Exclude already disliked
        )

        # Additional filters can be added here (e.g., industry, skills)
        industry = self.request.query_params.get("industry")
        if industry:
            potential_matches = potential_matches.filter(industry=industry)

        # Return shuffled results for variety
        return potential_matches.order_by("?")
