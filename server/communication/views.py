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

# Add these imports to the top of views.py

from django.db import transaction
from django.db.models import Q
from rest_framework.decorators import action

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

import uuid
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions

from .models import Room, Message
from .serializers import MessageSerializer

# Import WebRTCConfig from the right location
from .webrtc_config import WebRTCConfig

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

        messages = Message.objects.filter(room=room).order_by("-sent_at")
        paginator = self.pagination_class()
        paginated_messages = paginator.paginate_queryset(messages, request)
        serializer = MessageSerializer(paginated_messages, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, room_id):
        """
        Add a new message to the room
        """
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

        # Prepare message data
        message_data = {
            "room": str(room.id),
            "sender": request.user.id,
            "content": request.data.get("content", ""),
            "message_type": request.data.get("message_type", "text"),
        }

        # Handle media attachments
        if "image" in request.FILES:
            message_data["image"] = request.FILES["image"]
            message_data["message_type"] = "image"
        elif "video" in request.FILES:
            message_data["video"] = request.FILES["video"]
            message_data["message_type"] = "video"
        elif "audio" in request.FILES:
            message_data["audio"] = request.FILES["audio"]
            message_data["message_type"] = "audio"

        # Use serializer for validation and creation
        serializer = MessageSerializer(data=message_data)

        try:
            serializer.is_valid(raise_exception=True)
            message = serializer.save()

            # Notify via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"room_{room.id}",
                {"type": "chat_message", "message": serializer.data},
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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

    @action(detail=True, methods=["GET"])
    def webrtc_config(self, request, pk=None):
        """Get WebRTC configuration for a room"""
        room = self.get_object()

        # Generate WebRTC configuration
        config = {
            "room_config": {
                "room_id": str(room.id),
                "name": room.name,
                "type": room.room_type,
            },
            "ice_servers": WebRTCConfig.get_ice_servers(),
            "media_constraints": WebRTCConfig.get_media_constraints(),
            "token": request.auth.key if request.auth else None,
        }

        return Response(config)


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


class WebRTCConfigView(APIView):
    """
    View to provide WebRTC configuration for a specific room
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, room_id):
        """
        Get WebRTC configuration for a room
        """
        try:
            # Check if the room exists and the user has access to it
            room = Room.objects.get(
                id=room_id, communication_participants__user=request.user
            )

            # Generate WebRTC configuration
            config = {
                "room_config": {
                    "room_id": str(room_id),
                    "name": room.name,
                    "type": room.room_type,
                },
                "ice_servers": WebRTCConfig.get_ice_servers(),
                "media_constraints": WebRTCConfig.get_media_constraints(),
                "token": request.auth.key if request.auth else None,
            }

            return Response(config)

        except Room.DoesNotExist:
            return Response(
                {
                    "error": f"Room with id {room_id} does not exist or you don't have access"
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error getting WebRTC config: {str(e)}")
            return Response(
                {"error": f"Failed to get WebRTC configuration: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Add to views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import IncomingCallNotification, Room
from .serializers import IncomingCallNotificationSerializer
import logging
from .notification_service import NotificationService


logger = logging.getLogger(__name__)


class IncomingCallNotificationView(APIView):
    """API for managing incoming call notifications"""

    permission_classes = [permissions.IsAuthenticated]

    # Updated POST method for IncomingCallNotificationView

    def post(self, request):
        """Create a new incoming call notification"""
        recipient_id = request.data.get("recipient_id")
        room_id = request.data.get("room_id")
        call_type = request.data.get("call_type", "video")
        device_token = request.data.get("device_token")

        # Add detailed debug logging
        logger.debug(
            f"Creating call notification: caller={request.user.id}, recipient={recipient_id}, room={room_id}"
        )

        # Validate required fields
        if not recipient_id:
            return Response(
                {"error": "recipient_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not room_id:
            return Response(
                {"error": "room_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get recipient user
            User = get_user_model()
            try:
                recipient = User.objects.get(id=recipient_id)
                logger.debug(f"Found recipient: {recipient.username}")
            except User.DoesNotExist:
                logger.error(f"Recipient user {recipient_id} not found")
                return Response(
                    {"error": f"User with id {recipient_id} does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get room
            try:
                room = Room.objects.get(id=room_id)
                logger.debug(f"Found room: {room.name}")
            except Room.DoesNotExist:
                logger.error(f"Room {room_id} not found")
                return Response(
                    {"error": f"Room with id {room_id} does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Verify user has access to this room
            if not Participant.objects.filter(room=room, user=request.user).exists():
                logger.warning(
                    f"User {request.user.id} does not have access to room {room_id}"
                )
                return Response(
                    {"error": "You do not have access to this room"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Check if recipient is a participant in the room
            if not Participant.objects.filter(room=room, user=recipient).exists():
                logger.warning(
                    f"Recipient {recipient_id} is not a participant in room {room_id}"
                )
                return Response(
                    {"error": "Recipient is not a participant in this room"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Cancel any existing pending notifications for this caller/recipient/room
            existing_notifications = IncomingCallNotification.objects.filter(
                caller=request.user, recipient=recipient, room=room, status="pending"
            )

            if existing_notifications.exists():
                logger.debug(
                    f"Cancelling {existing_notifications.count()} existing notifications"
                )
                existing_notifications.update(status="expired")

            # Set expiration time (60 seconds from now)
            expires_at = timezone.now() + timedelta(seconds=60)

            # Create notification with transaction to ensure it's saved properly
            with transaction.atomic():
                notification = IncomingCallNotification.objects.create(
                    caller=request.user,
                    recipient=recipient,
                    room=room,
                    call_type=call_type,
                    expires_at=expires_at,
                    device_token=device_token,
                )

                logger.debug(f"Created notification: {notification.id}")

            # Serialize notification
            serializer = IncomingCallNotificationSerializer(notification)

            # Send notification via WebSocket to user
            channel_layer = get_channel_layer()
            user_group_name = f"user_{recipient.id}"

            async_to_sync(channel_layer.group_send)(
                user_group_name,
                {"type": "incoming_call", "notification": serializer.data},
            )
            logger.debug(f"Sent WebSocket notification to {user_group_name}")

            # If it's a direct room, also send to room group
            if room.room_type == "direct":
                room_group_name = f"room_{room.id}"
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {"type": "incoming_call", "notification": serializer.data},
                )
                logger.debug(f"Sent WebSocket notification to room {room_group_name}")

            # Send push notification for mobile devices
            if device_token:
                push_sent = NotificationService.send_incoming_call_notification(
                    device_token=device_token,
                    caller=request.user,
                    recipient=recipient,
                    call_type=call_type,
                    room_name=room.name,
                    notification_id=notification.id,
                )
                logger.debug(f"Push notification sent: {push_sent}")

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(
                f"Error creating incoming call notification: {str(e)}", exc_info=True
            )
            return Response(
                {"error": f"Failed to create call notification: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, notification_id=None):
        """Update notification status (accept, decline, etc.)"""
        if not notification_id:
            return Response(
                {"error": "notification_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Find notification
            notification = IncomingCallNotification.objects.get(
                id=notification_id,
                recipient=request.user,  # Must be the recipient to update
            )

            # Check if expired
            if notification.is_expired():
                notification.status = "expired"
                notification.save()
                serializer = IncomingCallNotificationSerializer(notification)
                return Response(serializer.data)

            # Update status
            status_action = request.data.get("status")
            if status_action in ["seen", "accepted", "declined", "missed"]:
                notification.status = status_action
                notification.save()

                # Notify caller via WebSocket about the status update
                channel_layer = get_channel_layer()
                user_group_name = f"user_{notification.caller.id}"

                serializer = IncomingCallNotificationSerializer(notification)

                async_to_sync(channel_layer.group_send)(
                    user_group_name,
                    {
                        "type": "call_notification_update",
                        "notification": serializer.data,
                    },
                )

                # If accepted, create a Call message in the room
                if status_action == "accepted":
                    from .models import Message

                    # Create call message
                    message = Message.objects.create(
                        room=notification.room,
                        sender=notification.caller,
                        message_type="call",
                        call_type=notification.call_type,
                        call_status="answered",
                    )

                    # Notify room about call being answered
                    from .serializers import MessageSerializer

                    message_serializer = MessageSerializer(message)

                    room_group_name = f"room_{notification.room.id}"
                    async_to_sync(channel_layer.group_send)(
                        room_group_name,
                        {"type": "call_notification", "call": message_serializer.data},
                    )

                return Response(serializer.data)
            else:
                return Response(
                    {
                        "error": f"Invalid status: {status_action}. Must be one of: seen, accepted, declined, missed"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except IncomingCallNotification.DoesNotExist:
            return Response(
                {
                    "error": f"Notification with id {notification_id} not found or you are not the recipient"
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error updating call notification: {str(e)}")
            return Response(
                {"error": f"Failed to update notification: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Updated GET method for IncomingCallNotificationView

    def get(self, request):
        """Get active and recent incoming call notifications for the current user"""
        # Add debug logging
        logger.debug(f"Retrieving call notifications for user {request.user.id}")

        # First, expire any outdated notifications
        self._expire_outdated_notifications(request.user)

        # Get active notifications (not expired and not ended)
        active_notifications = IncomingCallNotification.objects.filter(
            recipient=request.user,
            status__in=["pending", "seen"],
            expires_at__gt=timezone.now(),
        ).order_by("-created_at")

        # Also get recent notifications (within the last hour, regardless of status)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_notifications = (
            IncomingCallNotification.objects.filter(
                recipient=request.user, created_at__gte=one_hour_ago
            )
            .exclude(id__in=[n.id for n in active_notifications])
            .order_by("-created_at")
        )

        # Debug logging
        logger.debug(f"Found {active_notifications.count()} active notifications")
        logger.debug(f"Found {recent_notifications.count()} recent notifications")

        # Combine and serialize
        all_notifications = list(active_notifications) + list(recent_notifications)
        serializer = IncomingCallNotificationSerializer(all_notifications, many=True)

        # Return with separate sections for active and recent
        return Response(
            {
                "active": IncomingCallNotificationSerializer(
                    active_notifications, many=True
                ).data,
                "recent": IncomingCallNotificationSerializer(
                    recent_notifications, many=True
                ).data,
                "all": serializer.data,
            }
        )

    def _expire_outdated_notifications(self, user):
        """Helper method to expire outdated notifications"""
        now = timezone.now()
        expired_count = IncomingCallNotification.objects.filter(
            recipient=user, status="pending", expires_at__lte=now
        ).update(status="expired")

        if expired_count > 0:
            logger.debug(
                f"Expired {expired_count} outdated notifications for user {user.id}"
            )

    # Add these methods to IncomingCallNotificationView class

    def delete(self, request, notification_id=None):
        """Delete a notification (mainly for testing and cleanup)"""
        if not notification_id:
            return Response(
                {"error": "notification_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Find notification
            notification = IncomingCallNotification.objects.get(id=notification_id)

            # Check if user is caller or recipient
            if (
                request.user != notification.caller
                and request.user != notification.recipient
            ):
                return Response(
                    {"error": "You do not have permission to delete this notification"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Delete it
            notification.delete()
            logger.debug(f"Deleted notification {notification_id}")

            return Response(status=status.HTTP_204_NO_CONTENT)

        except IncomingCallNotification.DoesNotExist:
            return Response(
                {"error": f"Notification with id {notification_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error deleting notification: {str(e)}")
            return Response(
                {"error": f"Failed to delete notification: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["GET"])
    def debug(self, request):
        """Debug endpoint to check all notifications and their status"""
        if not request.user.is_staff:
            return Response(
                {"error": "Staff access required"}, status=status.HTTP_403_FORBIDDEN
            )

        # Get all notifications for the user in the last 24 hours
        day_ago = timezone.now() - timedelta(days=1)

        notifications = IncomingCallNotification.objects.filter(
            Q(recipient=request.user) | Q(caller=request.user), created_at__gte=day_ago
        ).order_by("-created_at")

        # Group by status
        status_counts = {}
        for notification in notifications:
            status_counts[notification.status] = (
                status_counts.get(notification.status, 0) + 1
            )

        # Get expired count
        now = timezone.now()
        expired_count = notifications.filter(
            status="pending", expires_at__lte=now
        ).count()

        # Group by whether they're expired or not
        expired_notifications = []
        non_expired_notifications = []
        for notification in notifications:
            if notification.expires_at <= now and notification.status == "pending":
                expired_notifications.append(notification)
            else:
                non_expired_notifications.append(notification)

        return Response(
            {
                "total_count": notifications.count(),
                "status_counts": status_counts,
                "should_be_expired_count": expired_count,
                "expired_notifications": IncomingCallNotificationSerializer(
                    expired_notifications, many=True
                ).data,
                "non_expired_notifications": IncomingCallNotificationSerializer(
                    non_expired_notifications, many=True
                ).data,
                "current_time": now.isoformat(),
            }
        )

    @action(detail=False, methods=["POST"])
    def expire_all(self, request):
        """Expire all pending notifications (for debugging)"""
        if not request.user.is_staff:
            return Response(
                {"error": "Staff access required"}, status=status.HTTP_403_FORBIDDEN
            )

        count = IncomingCallNotification.objects.filter(
            Q(recipient=request.user) | Q(caller=request.user), status="pending"
        ).update(status="expired")

        return Response(
            {"expired_count": count, "message": f"Expired {count} notifications"}
        )


# Updated IncomingCallNotificationView as ViewSet

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


class IncomingCallNotificationViewSet(viewsets.ModelViewSet):
    """API for managing incoming call notifications"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = IncomingCallNotificationSerializer

    def get_queryset(self):
        """Filter notifications to only those for the current user"""
        return IncomingCallNotification.objects.filter(
            Q(recipient=self.request.user) | Q(caller=self.request.user)
        ).order_by("-created_at")

    def list(self, request):
        """Get active and recent incoming call notifications for the current user"""
        # Add debug logging
        logger.info(f"Retrieving call notifications for user {request.user.id}")

        # First, expire any outdated notifications
        self._expire_outdated_notifications(request.user)

        # Get active notifications (not expired and not ended)
        active_notifications = IncomingCallNotification.objects.filter(
            recipient=request.user,
            status__in=["pending", "seen"],
            expires_at__gt=timezone.now(),
        ).order_by("-created_at")

        # Also get recent notifications (within the last hour, regardless of status)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_notifications = (
            IncomingCallNotification.objects.filter(
                Q(recipient=request.user) | Q(caller=request.user),
                created_at__gte=one_hour_ago,
            )
            .exclude(id__in=[n.id for n in active_notifications])
            .order_by("-created_at")
        )

        # Debug logging
        logger.info(f"Found {active_notifications.count()} active notifications")
        logger.info(f"Found {recent_notifications.count()} recent notifications")

        # Serialize notifications
        active_serializer = self.get_serializer(active_notifications, many=True)
        recent_serializer = self.get_serializer(recent_notifications, many=True)
        all_notifications = list(active_notifications) + list(recent_notifications)
        all_serializer = self.get_serializer(all_notifications, many=True)

        # Return with separate sections for active and recent
        return Response(
            {
                "active": active_serializer.data,
                "recent": recent_serializer.data,
                "all": all_serializer.data,
            }
        )

    def create(self, request):
        """Create a new incoming call notification"""
        recipient_id = request.data.get("recipient_id")
        room_id = request.data.get("room_id")
        call_type = request.data.get("call_type", "video")
        device_token = request.data.get("device_token")

        # Add detailed debug logging
        logger.info(
            f"Creating call notification: caller={request.user.id}, recipient={recipient_id}, room={room_id}"
        )

        # Validate required fields
        if not recipient_id:
            return Response(
                {"error": "recipient_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not room_id:
            return Response(
                {"error": "room_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get recipient user
            User = get_user_model()
            try:
                recipient = User.objects.get(id=recipient_id)
                logger.info(f"Found recipient: {recipient.username}")
            except User.DoesNotExist:
                logger.error(f"Recipient user {recipient_id} not found")
                return Response(
                    {"error": f"User with id {recipient_id} does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get room
            try:
                room = Room.objects.get(id=room_id)
                logger.info(f"Found room: {room.name}")
            except Room.DoesNotExist:
                logger.error(f"Room {room_id} not found")
                return Response(
                    {"error": f"Room with id {room_id} does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Verify user has access to this room
            if not Participant.objects.filter(room=room, user=request.user).exists():
                logger.warning(
                    f"User {request.user.id} does not have access to room {room_id}"
                )
                return Response(
                    {"error": "You do not have access to this room"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Check if recipient is a participant in the room
            if not Participant.objects.filter(room=room, user=recipient).exists():
                logger.warning(
                    f"Recipient {recipient_id} is not a participant in room {room_id}"
                )
                return Response(
                    {"error": "Recipient is not a participant in this room"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Cancel any existing pending notifications for this caller/recipient/room
            existing_notifications = IncomingCallNotification.objects.filter(
                caller=request.user, recipient=recipient, room=room, status="pending"
            )

            if existing_notifications.exists():
                logger.info(
                    f"Cancelling {existing_notifications.count()} existing notifications"
                )
                existing_notifications.update(status="expired")

            # Set expiration time (60 seconds from now)
            expires_at = timezone.now() + timedelta(seconds=60)

            # Create notification with transaction to ensure it's saved properly
            with transaction.atomic():
                notification = IncomingCallNotification.objects.create(
                    caller=request.user,
                    recipient=recipient,
                    room=room,
                    call_type=call_type,
                    expires_at=expires_at,
                    device_token=device_token,
                )

                logger.info(f"Created notification: {notification.id}")

            # Serialize notification
            serializer = self.get_serializer(notification)

            # Send notification via WebSocket to user
            channel_layer = get_channel_layer()
            user_group_name = f"user_{recipient.id}"

            async_to_sync(channel_layer.group_send)(
                user_group_name,
                {"type": "incoming_call", "notification": serializer.data},
            )
            logger.info(f"Sent WebSocket notification to {user_group_name}")

            # Also send as room_call_announcement to support frontend integration
            room_group_name = f"room_{room.id}"
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {"type": "room_call_announcement", "notification": serializer.data},
            )
            logger.info(f"Sent room_call_announcement to {room_group_name}")

            # If it's a direct room, also send to room group as incoming_call
            if room.room_type == "direct":
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {"type": "incoming_call", "notification": serializer.data},
                )
                logger.info(f"Sent WebSocket notification to room {room_group_name}")

            # Send push notification for mobile devices
            if device_token:
                push_sent = NotificationService.send_incoming_call_notification(
                    device_token=device_token,
                    caller=request.user,
                    recipient=recipient,
                    call_type=call_type,
                    room_name=room.name,
                    notification_id=notification.id,
                )
                logger.info(f"Push notification sent: {push_sent}")

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(
                f"Error creating incoming call notification: {str(e)}", exc_info=True
            )
            return Response(
                {"error": f"Failed to create call notification: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def update(self, request, pk=None):
        """Update notification status (accept, decline, etc.)"""
        try:
            # Find notification
            notification = self.get_object()

            # Only recipient can update status (with the exception of 'ended' status)
            status_action = request.data.get("status")
            if request.user != notification.recipient and (
                status_action != "ended" or notification.status != "accepted"
            ):
                return Response(
                    {
                        "error": "Only the recipient can update notification status (except ending an accepted call)"
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Check if expired
            if notification.is_expired() and status_action not in ["missed", "ended"]:
                notification.status = "expired"
                notification.save()
                serializer = self.get_serializer(notification)
                return Response(serializer.data)

            # Update status
            if status_action in ["seen", "accepted", "declined", "missed", "ended"]:
                old_status = notification.status
                notification.status = status_action
                notification.save()

                logger.info(
                    f"Updated call notification {notification.id} status from {old_status} to {status_action}"
                )

                # Remaining implementation...

                # Notify caller via WebSocket about the status update
                channel_layer = get_channel_layer()
                user_group_name = f"user_{notification.caller.id}"

                serializer = self.get_serializer(notification)

                async_to_sync(channel_layer.group_send)(
                    user_group_name,
                    {
                        "type": "call_notification_update",
                        "notification": serializer.data,
                    },
                )

                # If accepted, create a Call message in the room
                if status_action == "accepted":
                    message = Message.objects.create(
                        room=notification.room,
                        sender=notification.caller,
                        message_type="call",
                        call_type=notification.call_type,
                        call_status="answered",
                    )

                    # Notify room about call being answered
                    from .serializers import MessageSerializer

                    message_serializer = MessageSerializer(message)

                    room_group_name = f"room_{notification.room.id}"
                    async_to_sync(channel_layer.group_send)(
                        room_group_name,
                        {"type": "call_notification", "call": message_serializer.data},
                    )

                    logger.info(
                        f"Created answered call message and sent notification for call {notification.id}"
                    )

                # If ended, calculate duration if it was accepted before
                if status_action == "ended" and old_status == "accepted":
                    # Find the related call message and update it
                    try:
                        call_message = (
                            Message.objects.filter(
                                room=notification.room,
                                sender=notification.caller,
                                message_type="call",
                                call_type=notification.call_type,
                                call_status="answered",
                            )
                            .order_by("-sent_at")
                            .first()
                        )

                        if call_message:
                            duration = int(
                                (timezone.now() - call_message.sent_at).total_seconds()
                            )
                            call_message.call_duration = duration
                            call_message.call_status = "ended"
                            call_message.save()

                            # Notify room about call ending
                            message_serializer = MessageSerializer(call_message)
                            room_group_name = f"room_{notification.room.id}"
                            async_to_sync(channel_layer.group_send)(
                                room_group_name,
                                {"type": "call_ended", "call": message_serializer.data},
                            )

                            logger.info(
                                f"Updated call message with duration {duration}s and sent call_ended notification"
                            )
                    except Exception as e:
                        logger.error(f"Error updating call message: {str(e)}")

                return Response(serializer.data)
            else:
                return Response(
                    {
                        "error": f"Invalid status: {status_action}. Must be one of: seen, accepted, declined, missed, ended"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.error(f"Error updating call notification: {str(e)}")
            return Response(
                {"error": f"Failed to update notification: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _expire_outdated_notifications(self, user):
        """Helper method to expire outdated notifications"""
        now = timezone.now()
        expired_count = IncomingCallNotification.objects.filter(
            status="pending", expires_at__lte=now
        ).update(status="expired")

        if expired_count > 0:
            logger.info(f"Expired {expired_count} outdated notifications")

    @action(detail=False, methods=["GET"])
    def debug(self, request):
        """Debug endpoint to check all notifications and their status"""
        if not request.user.is_staff:
            return Response(
                {"error": "Staff access required"}, status=status.HTTP_403_FORBIDDEN
            )

        # Get all notifications for the user in the last 24 hours
        day_ago = timezone.now() - timedelta(days=1)

        notifications = IncomingCallNotification.objects.filter(
            Q(recipient=request.user) | Q(caller=request.user), created_at__gte=day_ago
        ).order_by("-created_at")

        # Group by status
        status_counts = {}
        for notification in notifications:
            status_counts[notification.status] = (
                status_counts.get(notification.status, 0) + 1
            )

        # Get expired count
        now = timezone.now()
        expired_count = notifications.filter(
            status="pending", expires_at__lte=now
        ).count()

        # Group by whether they're expired or not
        expired_notifications = []
        non_expired_notifications = []
        for notification in notifications:
            if notification.expires_at <= now and notification.status == "pending":
                expired_notifications.append(notification)
            else:
                non_expired_notifications.append(notification)

        return Response(
            {
                "total_count": notifications.count(),
                "status_counts": status_counts,
                "should_be_expired_count": expired_count,
                "expired_notifications": self.get_serializer(
                    expired_notifications, many=True
                ).data,
                "non_expired_notifications": self.get_serializer(
                    non_expired_notifications, many=True
                ).data,
                "current_time": now.isoformat(),
            }
        )

    @action(detail=False, methods=["POST"])
    def expire_all(self, request):
        """Expire all pending notifications (for debugging)"""
        if not request.user.is_staff:
            return Response(
                {"error": "Staff access required"}, status=status.HTTP_403_FORBIDDEN
            )

        count = IncomingCallNotification.objects.filter(
            Q(recipient=request.user) | Q(caller=request.user), status="pending"
        ).update(status="expired")

        return Response(
            {"expired_count": count, "message": f"Expired {count} notifications"}
        )

    @action(detail=False, methods=["POST"])
    def expire_all(self, request):
        """Expire all pending notifications (for debugging)"""
        if not request.user.is_staff:
            return Response(
                {"error": "Staff access required"}, status=status.HTTP_403_FORBIDDEN
            )

        count = IncomingCallNotification.objects.filter(
            Q(recipient=request.user) | Q(caller=request.user), status="pending"
        ).update(status="expired")

        return Response(
            {"expired_count": count, "message": f"Expired {count} notifications"}
        )

    # Add the new method here
    @action(detail=False, methods=["GET"])
    def active_calls(self, request):
        """Show currently active calls for debugging"""
        if not request.user.is_staff:
            return Response(
                {"error": "Staff access required"}, status=status.HTTP_403_FORBIDDEN
            )

        # Get all active notifications
        active = IncomingCallNotification.objects.filter(
            status__in=["pending", "seen", "accepted"], expires_at__gt=timezone.now()
        ).order_by("-created_at")

        serializer = self.get_serializer(active, many=True)
        return Response(
            {
                "count": active.count(),
                "calls": serializer.data,
                "current_time": timezone.now().isoformat(),
            }
        )
