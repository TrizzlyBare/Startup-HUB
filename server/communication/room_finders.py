from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.contrib.auth import get_user_model

from .models import Room
from .serializers import RoomSerializer
import logging

import uuid
from rest_framework import serializers


logger = logging.getLogger(__name__)


class FindDirectRoomView(APIView):
    """Find a direct message room between users"""

    permission_classes = [permissions.IsAuthenticated]

    def validate_room_id(self, room_id):
        """
        Clean and validate room_id UUID
        """
        try:
            # Remove trailing slash and validate UUID
            cleaned_room_id = str(room_id).rstrip("/")
            return uuid.UUID(cleaned_room_id)
        except (ValueError, AttributeError):
            raise serializers.ValidationError("Invalid room ID format")

    def get(self, request):
        """Find direct message room between current user and another user"""
        other_username = request.query_params.get("username")

        if not other_username:
            return Response(
                {"error": "Username parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get the other user
            User = get_user_model()
            other_user = User.objects.get(username=other_username)

            # Find direct room between current user and other user
            room = (
                Room.objects.filter(
                    room_type="direct", communication_participants__user=request.user
                )
                .filter(communication_participants__user=other_user)
                .first()
            )

            if not room:
                return Response(
                    {"error": f"No direct room found with user {other_username}"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = RoomSerializer(room)
            return Response(serializer.data)

        except User.DoesNotExist:
            return Response(
                {"error": f"User {other_username} does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def post(self, request):
        """Find or create a direct message room between two users by usernames"""
        username1 = request.data.get("username1")
        username2 = request.data.get("username2")

        if not username1 or not username2:
            return Response(
                {"error": "Both username1 and username2 are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get the user objects
            User = get_user_model()
            user1 = User.objects.get(username=username1)
            user2 = User.objects.get(username=username2)

            # Find rooms where both users are participants
            # and the room type is "direct"
            room = (
                Room.objects.filter(
                    room_type="direct", communication_participants__user=user1
                )
                .filter(communication_participants__user=user2)
                .first()
            )

            # If room doesn't exist, create it
            if not room:
                # Create room name using alphabetically sorted usernames
                sorted_names = sorted([username1, username2])
                room_name = f"Chat between {sorted_names[0]} and {sorted_names[1]}"

                # Create the room
                room = Room.objects.create(name=room_name, room_type="direct")

                # Add participants
                from .models import Participant

                Participant.objects.create(user=user1, room=room)
                Participant.objects.create(user=user2, room=room)

                logger.info(
                    f"Created new direct room between {username1} and {username2}"
                )

            serializer = RoomSerializer(room)
            return Response(serializer.data)

        except User.DoesNotExist as e:
            return Response(
                {"error": f"User does not exist: {str(e)}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error finding/creating direct room: {str(e)}")
            return Response(
                {"error": f"Failed to process request: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FindGroupRoomsView(APIView):
    """Find group rooms the current user is a participant in"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Find group rooms the current user is a participant in"""
        # Get all group rooms (non-direct) the user is part of
        rooms = Room.objects.filter(
            room_type__in=["group", "video"],  # All non-direct room types
            communication_participants__user=request.user,
        ).distinct()

        if not rooms.exists():
            return Response(
                {
                    "message": "You are not a participant in any group rooms",
                    "rooms": [],
                },
                status=status.HTTP_200_OK,
            )

        serializer = RoomSerializer(rooms, many=True)
        return Response({"rooms": serializer.data})


class FindRoomByNameView(APIView):
    """Find a room by its name (partial match)"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Find a room by its name (partial match)"""
        room_name = request.query_params.get("name")

        if not room_name:
            return Response(
                {"error": "Room name parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find rooms that match the name (case-insensitive)
        rooms = Room.objects.filter(
            name__icontains=room_name,
            communication_participants__user=request.user,  # Only rooms user has access to
        ).distinct()

        if not rooms.exists():
            return Response(
                {"message": f"No rooms found matching '{room_name}'", "rooms": []},
                status=status.HTTP_200_OK,
            )

        serializer = RoomSerializer(rooms, many=True)
        return Response({"rooms": serializer.data})


class UserRoomsView(APIView):
    """Get all rooms the user is a participant in, organized by type"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get all rooms the user is a participant in, organized by type"""
        # Get all rooms the user is part of
        user_rooms = Room.objects.filter(
            communication_participants__user=request.user
        ).prefetch_related("communication_participants__user")

        # Split into direct and group rooms
        direct_rooms = []
        group_rooms = []

        for room in user_rooms:
            if room.room_type == "direct":
                direct_rooms.append(room)
            else:
                group_rooms.append(room)

        # Serialize rooms
        direct_serializer = RoomSerializer(direct_rooms, many=True)
        group_serializer = RoomSerializer(group_rooms, many=True)

        return Response(
            {
                "direct_rooms": direct_serializer.data,
                "group_rooms": group_serializer.data,
            }
        )
