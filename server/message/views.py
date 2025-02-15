from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from .models import Room, Message, Participant
from .serializers import (
    RoomSerializer,
    RoomCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    ParticipantSerializer,
)


class RoomViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return RoomCreateSerializer
        return RoomSerializer

    def get_queryset(self):
        user = self.request.user
        return Room.objects.filter(participants__user=user).order_by("-updated_at")

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        room = self.get_object()
        user = request.user

        if not Participant.objects.filter(room=room, user=user).exists():
            Participant.objects.create(room=room, user=user)
            return Response({"status": "joined"})
        return Response({"status": "already joined"})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        room = self.get_object()
        Participant.objects.filter(room=room, user=request.user).delete()
        return Response({"status": "left"})


class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return MessageCreateSerializer
        return MessageSerializer

    def get_queryset(self):
        room_id = self.kwargs.get("room_pk")
        return (
            Message.objects.filter(room_id=room_id)
            .select_related("sender", "receiver")
            .order_by("-sent_at")
        )

    def create(self, request, *args, **kwargs):
        room = get_object_or_404(Room, id=self.kwargs.get("room_pk"))
        serializer = self.get_serializer(data={**request.data, "room": room.id})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Update room's updated_at timestamp
        room.save()  # This triggers the auto_now field

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ParticipantViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantSerializer

    def get_queryset(self):
        room_id = self.kwargs.get("room_pk")
        return Participant.objects.filter(room_id=room_id).select_related("user")

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None, room_pk=None):
        participant = self.get_object()
        participant.mark_messages_as_read()
        return Response({"status": "marked as read"})
