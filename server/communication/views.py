from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
from django.db import transaction
from rest_framework.pagination import PageNumberPagination

from .models import Room, Message, Participant, CallLog, CallInvitation
from .serializers import (
    RoomSerializer,
    MessageSerializer,
    CallLogSerializer,
    CallInvitationSerializer,
    ParticipantSerializer,
)

from .models import MediaFile
from .serializers import MediaFileSerializer

from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response

# Set up logging
logger = logging.getLogger(__name__)


class UsernameLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")

        User = get_user_model()
        try:
            # Find user by username
            user = User.objects.get(username=username)

            return Response(
                {"username": user.username, "message": "Login successful"},
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            # Optional: Auto-create user if not exists
            try:
                user = User.objects.create_user(username=username)
                return Response(
                    {"username": user.username, "message": "User created successfully"},
                    status=status.HTTP_201_CREATED,
                )
            except Exception as e:
                return Response(
                    {"error": "User creation failed", "details": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )


class MessagePagination(PageNumberPagination):
    """
    Custom pagination class for messages
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class RoomViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def get_queryset(self):
        return Room.objects.filter(communication_participants__user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """
        Override retrieve to make sure the object exists and user has access
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["GET"])
    def messages(self, request, pk=None):
        """
        Retrieve messages for a specific room with pagination
        """
        room = self.get_object()

        # Get messages ordered by sent_at in descending order
        messages = Message.objects.filter(room=room).order_by("-sent_at")

        # Use the same pagination as MessageViewSet
        paginator = MessagePagination()
        paginated_messages = paginator.paginate_queryset(messages, request)

        serializer = MessageSerializer(paginated_messages, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=["POST"])
    def create_direct_message(self, request):
        recipient_id = request.data.get("recipient_id")

        # Check for existing direct message room
        existing_room = (
            Room.objects.filter(
                room_type="direct", communication_participants__user=request.user
            )
            .filter(communication_participants__user_id=recipient_id)
            .first()
        )

        if existing_room:
            serializer = self.get_serializer(existing_room)
            return Response(serializer.data)

        # Create new room
        room = Room.objects.create(
            name=f"Chat between {request.user.username} and {recipient_id}",
            room_type="direct",
        )

        # Add participants
        Participant.objects.create(user=request.user, room=room)
        Participant.objects.create(user_id=recipient_id, room=room)

        serializer = self.get_serializer(room)
        return Response(serializer.data)

    @action(detail=False, methods=["POST"])
    def create_direct_chat(self, request):
        """
        Create a direct message room between two users
        """
        recipient_id = request.data.get("recipient_id")

        # Check for existing direct message room
        existing_room = (
            Room.objects.filter(
                room_type="direct", communication_participants__user=request.user
            )
            .filter(communication_participants__user_id=recipient_id)
            .first()
        )

        if existing_room:
            serializer = self.get_serializer(existing_room)
            return Response(serializer.data)

        # Create new room
        room = Room.objects.create(
            name=f"Chat between {request.user.username} and {recipient_id}",
            room_type="direct",
        )

        # Add participants
        Participant.objects.create(user=request.user, room=room)
        Participant.objects.create(user_id=recipient_id, room=room)

        serializer = self.get_serializer(room)
        return Response(serializer.data)

    @action(detail=True, methods=["POST"], url_path="send_message")
    def send_message(self, request, pk=None):
        """
        Send a message to a room
        """
        try:
            room = self.get_object()
            message_type = request.data.get("message_type", "text")

            # Handle different message types
            message_data = {
                "room": room,
                "sender": request.user,
                "content": request.data.get("content", ""),
                "message_type": message_type,
            }

            # Handle media uploads
            if message_type == "image" and request.FILES.get("image"):
                message_data["image"] = request.FILES["image"]
            elif message_type == "video" and request.FILES.get("video"):
                message_data["video"] = request.FILES["video"]

            message = Message.objects.create(**message_data)

            # Notify via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"room_{room.id}",
                {"type": "chat_message", "message": MessageSerializer(message).data},
            )

            return Response(
                MessageSerializer(message).data, status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error in send_message: {str(e)}")
            return Response(
                {"error": f"Failed to send message: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["POST"], url_path="add_participant")
    def add_participant(self, request, pk=None):
        """
        Add a participant to a room
        """
        try:
            # Log incoming request data for debugging
            logger.info(f"add_participant called with data: {request.data}")

            # Get room directly from pk in URL rather than using get_object()
            try:
                room = Room.objects.get(pk=pk)
                logger.info(f"Found room with id: {room.id}")
            except Room.DoesNotExist:
                logger.error(f"Room with id {pk} does not exist")
                return Response(
                    {"error": f"Room with id {pk} does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Get username from request data
            username = request.data.get("username")
            user_id = None

            if username:
                # If username is provided, lookup user by username
                try:
                    from django.contrib.auth import get_user_model

                    User = get_user_model()
                    user = User.objects.get(username=username)
                    user_id = user.id
                    logger.info(f"Found user by username: {username}, id: {user_id}")
                except User.DoesNotExist:
                    logger.warning(f"User with username {username} does not exist")
                    return Response(
                        {"error": f"User with username {username} does not exist"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                # If no username, try user_id
                user_id = request.data.get("user_id")
                if not user_id:
                    logger.warning("Neither username nor user_id was provided")
                    return Response(
                        {"error": "Either username or user_id is required"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Check if the user_id is valid
                try:
                    from django.contrib.auth import get_user_model

                    User = get_user_model()
                    user = User.objects.get(id=user_id)
                    logger.info(
                        f"Found user by id: {user.id}, username: {user.username}"
                    )
                except User.DoesNotExist:
                    logger.warning(f"User with id {user_id} does not exist")
                    return Response(
                        {"error": f"User with id {user_id} does not exist"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

            # Check if user is already in the room - do this before starting transaction
            if Participant.objects.filter(room=room, user_id=user_id).exists():
                logger.info(
                    f"User {user_id} is already a participant in room {room.id}"
                )
                return Response(
                    {"message": "User is already a participant in this room"},
                    status=status.HTTP_200_OK,
                )

            # Check if room has reached max participants - do this before starting transaction
            if (
                room.max_participants > 0
                and room.communication_participants.count() >= room.max_participants
            ):
                logger.warning(
                    f"Room {room.id} has reached maximum number of participants ({room.max_participants})"
                )
                return Response(
                    {"error": "Room has reached maximum number of participants"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Use transaction to ensure atomicity for just the database update
            participant = None
            with transaction.atomic():
                # Add participant
                is_admin = request.data.get("is_admin", False)
                logger.info(
                    f"Creating participant with user_id={user_id}, room_id={room.id}, is_admin={is_admin}"
                )

                participant = Participant.objects.create(
                    user_id=user_id, room=room, is_admin=is_admin
                )

            # Successfully created participant, now notify via WebSocket
            if participant:
                logger.info(f"Participant created successfully: {participant.id}")

                # Notify other participants via WebSocket - OUTSIDE the transaction
                try:
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
                except Exception as e:
                    logger.error(f"Error sending WebSocket notification: {str(e)}")
                    # Continue with the response even if notification fails

            return Response(
                {"message": "Participant added successfully"},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Unexpected error in add_participant: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return Response(
                {"error": f"Failed to add participant: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["POST"])
    def start_call(self, request, pk=None):
        room = self.get_object()
        call_type = request.data.get("call_type", "video")

        # Find the other participant in the room
        other_participant = room.communication_participants.exclude(
            user=request.user
        ).first()

        # Create call log
        call_log = CallLog.objects.create(
            caller=request.user,
            receiver=other_participant.user,
            call_type=call_type,
            status="initiated",
        )

        # Notify via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"room_{room.id}",
            {"type": "call_notification", "call": CallLogSerializer(call_log).data},
        )

        return Response(CallLogSerializer(call_log).data)

    @action(detail=True, methods=["POST"])
    def create_call_invitation(self, request, pk=None):
        room = self.get_object()
        call_type = request.data.get("call_type", "video")
        invitee_id = request.data.get("invitee_id")

        if not invitee_id:
            return Response(
                {"error": "Invitee ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create invitation with 60 second expiry
        expires_at = timezone.now() + timedelta(seconds=60)

        invitation = CallInvitation.objects.create(
            inviter=request.user,
            invitee_id=invitee_id,
            room=room,
            call_type=call_type,
            expires_at=expires_at,
        )

        # Notify via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{invitee_id}",
            {
                "type": "call_invitation",
                "invitation": CallInvitationSerializer(invitation).data,
            },
        )

        return Response(CallInvitationSerializer(invitation).data)


class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    pagination_class = MessagePagination

    def get_queryset(self):
        """
        This allows filtering messages by room_id both as a URL parameter
        and as a query parameter
        """
        room_id = self.kwargs.get("room_id") or self.request.query_params.get("room_id")
        if room_id:
            # Also verify that the user has access to this room
            queryset = Message.objects.filter(
                room_id=room_id,
                room__communication_participants__user=self.request.user,
            ).order_by("-sent_at")
            return queryset
        # Return empty queryset if no room_id specified
        return Message.objects.none()

    def perform_create(self, serializer):
        """
        Override perform_create to ensure the sender is set to the current user
        """
        serializer.save(sender=self.request.user)


class MediaFileViewSet(viewsets.ModelViewSet):
    queryset = MediaFile.objects.all()
    serializer_class = MediaFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        """
        Add optional transformation parameters
        """
        context = super().get_serializer_context()
        context["width"] = self.request.query_params.get("width")
        context["height"] = self.request.query_params.get("height")
        return context

    def perform_create(self, serializer):
        serializer.save()
