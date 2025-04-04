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

    @action(detail=False, methods=["POST"])
    def create_direct_message(self, request):
        recipient_id = request.data.get("recipient_id")

        # Check for existing direct message room
        existing_room = (
            Room.objects.filter(room_type="direct", participants__user=request.user)
            .filter(participants__user_id=recipient_id)
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

    @action(detail=True, methods=["POST"])
    def send_message(self, request, pk=None):
        room = self.get_object()
        message_type = request.data.get("message_type", "text")

        # Handle different message types
        message_data = {
            "room": room,
            "sender": request.user,
            "content": request.data.get("content"),
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

        return Response(MessageSerializer(message).data)

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


class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def get_queryset(self):
        room_id = self.request.query_params.get("room_id")
        return Message.objects.filter(room_id=room_id).order_by("-sent_at")


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
