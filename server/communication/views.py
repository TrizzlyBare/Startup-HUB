from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Room, Message, Participant, CallLog, CallInvitation
from .serializers import (
    RoomSerializer,
    MessageSerializer,
    CallLogSerializer,
    CallInvitationSerializer,
)

from .models import MediaFile
from .serializers import MediaFileSerializer

from django.utils import timezone
from datetime import timedelta


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
            return Response(
                {"error": f"Failed to send message: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["POST"])
    def start_call(self, request, pk=None):
        room = self.get_object()
        call_type = request.data.get("call_type", "video")

        # Find the other participant in the room
        other_participant = room.participants.exclude(user=request.user).first()

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
    
    @action(detail=True, methods=["POST"], url_path="add_participant")
    def add_participant(self, request, pk=None):
        """
        Add a participant to a room
        """
        try:
            room = self.get_object()
            user_id = request.data.get("user_id")
            
            if not user_id:
                return Response(
                    {"error": "user_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Check if user is already in the room
            if Participant.objects.filter(room=room, user_id=user_id).exists():
                return Response(
                    {"message": "User is already a participant in this room"},
                    status=status.HTTP_200_OK
                )
                
            # Check if room has reached max participants
            if room.max_participants > 0 and room.communication_participants.count() >= room.max_participants:
                return Response(
                    {"error": "Room has reached maximum number of participants"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Add participant
            is_admin = request.data.get("is_admin", False)
            participant = Participant.objects.create(
                user_id=user_id,
                room=room,
                is_admin=is_admin
            )
            
            # Notify other participants via WebSocket if needed
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"room_{room.id}",
                {
                    "type": "participant_added",
                    "participant": {
                        "user_id": str(participant.user.id),
                        "username": participant.user.username,
                        "is_admin": participant.is_admin
                    }
                },
            )
            
            return Response(
                {"message": "Participant added successfully"},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to add participant: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

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

    def create(self, request, *args, **kwargs):
        """
        Create a new message, ensuring room_id from URL is used if present
        """
        room_id = self.kwargs.get("room_id")
        if room_id and "room" not in request.data:
            request.data["room"] = room_id

        return super().create(request, *args, **kwargs)


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
