from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
from django.db import transaction
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
import uuid

from .models import Room, Message, Participant, CallLog, CallInvitation, MediaFile
from .serializers import (
    RoomSerializer,
    MessageSerializer,
    CallLogSerializer,
    CallInvitationSerializer,
    ParticipantSerializer,
    MediaFileSerializer,
)

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

# Set up logging
logger = logging.getLogger(__name__)


class MessagePagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 100


class UsernameLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")

        User = get_user_model()
        try:
            # Find or create user by username
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": f"{username}@example.com"}
            )

            # Always generate a token
            token, _ = Token.objects.get_or_create(user=user)

            return Response(
                {
                    "username": user.username,
                    "token": token.key,
                    "created": created,
                    "message": "Login successful",
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": "Login failed", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DirectRoomView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Get direct message rooms for the current user
        """
        # Get all direct message rooms the user is part of
        direct_rooms = Room.objects.filter(
            room_type="direct", communication_participants__user=request.user
        ).distinct()

        serializer = RoomSerializer(direct_rooms, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Create or retrieve a direct message room between the current user and another user
        """
        recipient_id = request.data.get("recipient_id")

        # Validate recipient_id
        if not recipient_id:
            return Response(
                {"error": "recipient_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get user model
        User = get_user_model()

        # Find recipient - don't try to use ID directly
        try:
            # Check if it's a UUID format
            try:
                uuid_obj = uuid.UUID(recipient_id)
                recipient = User.objects.get(id=uuid_obj)
            except (ValueError, TypeError):
                # Not a valid UUID, try to find user by username
                recipient = User.objects.get(username=recipient_id)

        except User.DoesNotExist:
            return Response(
                {"error": f"User with id or username '{recipient_id}' does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Rest of the existing code...
        # Check for existing direct message room
        existing_room = (
            Room.objects.filter(
                room_type="direct", communication_participants__user=request.user
            )
            .filter(communication_participants__user=recipient)
            .first()
        )

        if existing_room:
            serializer = RoomSerializer(existing_room)
            return Response(serializer.data)

        # Ensure consistent room naming by sorting usernames
        sorted_names = sorted([request.user.username, recipient.username])
        room_name = f"Chat between {sorted_names[0]} and {sorted_names[1]}"

        # Create new room with a valid UUID
        room = Room.objects.create(
            id=uuid.uuid4(),
            name=room_name,
            room_type="direct",
        )

        # Add participants
        Participant.objects.create(user=request.user, room=room)
        Participant.objects.create(user=recipient, room=room)

        serializer = RoomSerializer(room)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RoomMessagesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MessagePagination

    def get(self, request, room_id):
        """
        Get messages for a specific room with pagination
        """
        # Validate room exists and user has access
        try:
            room = Room.objects.get(
                id=room_id, communication_participants__user=request.user
            )
        except Room.DoesNotExist:
            return Response(
                {
                    "error": f"Room with id {room_id} does not exist or you don't have access"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get messages ordered by sent_at
        messages = Message.objects.filter(room=room).order_by("-sent_at")

        # Use pagination
        paginator = self.pagination_class()
        paginated_messages = paginator.paginate_queryset(messages, request)

        serializer = MessageSerializer(paginated_messages, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, room_id):
        """
        Add a new message to the room
        """
        # Validate room exists and user has access
        try:
            room = Room.objects.get(
                id=room_id, communication_participants__user=request.user
            )
        except Room.DoesNotExist:
            return Response(
                {
                    "error": f"Room with id {room_id} does not exist or you don't have access"
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Create message
        message_type = request.data.get("message_type", "text")
        content = request.data.get("content", "")

        message_data = {
            "room": room,
            "sender": request.user,
            "content": content,
            "message_type": message_type,
        }

        # Handle media attachments
        if message_type == "image" and request.FILES.get("image"):
            from .utils import MediaProcessor

            image_url = MediaProcessor.upload_image(request.FILES["image"])
            if image_url:
                message_data["image"] = image_url

        elif message_type == "video" and request.FILES.get("video"):
            from .utils import MediaProcessor

            video_result = MediaProcessor.upload_video(request.FILES["video"])
            if video_result:
                message_data["video"] = video_result.get("video_url")

        elif message_type == "audio" and request.FILES.get("audio"):
            from .utils import MediaProcessor

            audio_url = MediaProcessor.upload_audio(request.FILES["audio"])
            if audio_url:
                message_data["audio"] = audio_url

        # Create the message
        message = Message.objects.create(**message_data)

        # Notify via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"room_{room.id}",
            {"type": "chat_message", "message": MessageSerializer(message).data},
        )

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class RoomViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def get_queryset(self):
        """Filter rooms to only those the user is a participant in"""
        return Room.objects.filter(communication_participants__user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to make sure the object exists and user has access"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Override create to ensure room has a valid UUID and at least one participant"""
        data = request.data.copy()

        # Ensure room has a valid UUID if not provided
        if not data.get("id"):
            data["id"] = str(uuid.uuid4())

        # Create the room
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        room = serializer.save()

        # Add the creator as a participant
        Participant.objects.create(user=request.user, room=room, is_admin=True)

        # Return the created room
        serializer = self.get_serializer(room)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["POST"], url_path="add_participant")
    def add_participant(self, request, pk=None):
        """Add a participant to a room"""
        try:
            room = self.get_object()

            # Get user ID from request data
            user_id = request.data.get("user_id")
            username = request.data.get("username")

            User = get_user_model()
            target_user = None

            # Try to find user by ID or username
            if user_id:
                try:
                    target_user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    return Response(
                        {"error": f"User with id {user_id} does not exist"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            elif username:
                try:
                    target_user = User.objects.get(username=username)
                except User.DoesNotExist:
                    return Response(
                        {"error": f"User with username {username} does not exist"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                return Response(
                    {"error": "Either user_id or username is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if user is already in the room
            if Participant.objects.filter(room=room, user=target_user).exists():
                return Response(
                    {"message": "User is already a participant in this room"},
                    status=status.HTTP_200_OK,
                )

            # Check room capacity
            if (
                room.max_participants > 0
                and room.communication_participants.count() >= room.max_participants
            ):
                return Response(
                    {"error": "Room has reached maximum number of participants"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add participant
            is_admin = request.data.get("is_admin", False)
            participant = Participant.objects.create(
                user=target_user, room=room, is_admin=is_admin
            )

            # Notify via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"room_{room.id}",
                {
                    "type": "participant_added",
                    "participant": {
                        "user_id": str(participant.user.id),
                        "username": participant.user.username,
                        "is_admin": participant.is_admin,
                    },
                },
            )

            return Response(
                ParticipantSerializer(participant).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Error in add_participant: {str(e)}")
            return Response(
                {"error": f"Failed to add participant: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["POST"])
    def start_call(self, request, pk=None):
        """Initiate a call in the room"""
        room = self.get_object()
        call_type = request.data.get("call_type", "video")

        # Create call invitation with 60 second expiry
        expires_at = timezone.now() + timedelta(seconds=60)

        # Get other participants
        other_participants = room.communication_participants.exclude(user=request.user)

        invitations = []
        for participant in other_participants:
            invitation = CallInvitation.objects.create(
                inviter=request.user,
                invitee=participant.user,
                room=room,
                call_type=call_type,
                expires_at=expires_at,
            )
            invitations.append(invitation)

            # Notify each participant via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{participant.user.id}",
                {
                    "type": "call_invitation",
                    "invitation": CallInvitationSerializer(invitation).data,
                },
            )

        # Also notify the room
        message = Message.objects.create(
            room=room,
            sender=request.user,
            message_type="call",
            call_type=call_type,
            call_status="initiated",
        )

        async_to_sync(channel_layer.group_send)(
            f"room_{room.id}",
            {"type": "call_notification", "call": MessageSerializer(message).data},
        )

        return Response(
            {
                "message": f"Call initiated in room {room.id}",
                "invitations": CallInvitationSerializer(invitations, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageSerializer
    pagination_class = MessagePagination

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

    def get_queryset(self):
        """Filter messages by room_id and verify user access"""
        room_id = self.request.query_params.get("room_id")
        if not room_id:
            return Message.objects.none()

        # Use the new validation method
        try:
            validated_room_id = self.validate_room_id(room_id)
        except serializers.ValidationError:
            return Message.objects.none()

        # Verify that the user has access to this room
        return Message.objects.filter(
            room_id=validated_room_id,
            room__communication_participants__user=self.request.user,
        ).order_by("-sent_at")

    def create(self, request, *args, **kwargs):
        """Override create to ensure room_id is valid and user has access"""
        # Get and validate room_id
        room_id = request.data.get("room_id")
        if not room_id:
            return Response(
                {"error": "room_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Use the new validation method
        try:
            validated_room_id = self.validate_room_id(room_id)
        except serializers.ValidationError:
            return Response(
                {"error": "Invalid room ID format"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Verify room exists and user has access
        try:
            room = Room.objects.get(
                id=validated_room_id, communication_participants__user=request.user
            )
        except Room.DoesNotExist:
            return Response(
                {"error": "Room does not exist or you don't have access"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Continue with message creation
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set sender and room explicitly
        self.perform_create(serializer)

        # Notify via WebSocket if successful
        message = serializer.instance
        if message:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"room_{room_id}",
                {"type": "chat_message", "message": serializer.data},
            )

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):
        """Set sender to current user and ensure room is set"""
        room_id = self.request.data.get("room_id")
        try:
            room = Room.objects.get(
                id=room_id, communication_participants__user=self.request.user
            )
            serializer.save(sender=self.request.user, room=room)
        except Room.DoesNotExist:
            raise serializers.ValidationError(
                {"room_id": "Room does not exist or you don't have access."}
            )


class MediaFileViewSet(viewsets.ModelViewSet):
    queryset = MediaFile.objects.all()
    serializer_class = MediaFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        """Add optional transformation parameters"""
        context = super().get_serializer_context()
        context["width"] = self.request.query_params.get("width")
        context["height"] = self.request.query_params.get("height")
        return context

    def perform_create(self, serializer):
        """Ensure the user is set"""
        serializer.save(user=self.request.user)


class FindDirectRoomView(APIView):
    """Find a direct message room between users"""

    permission_classes = [permissions.IsAuthenticated]

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
