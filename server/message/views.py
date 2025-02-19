from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Exists, OuterRef
from django.utils import timezone

from .models import Room, Message, Participant, MessageReceipt
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

    @action(detail=False, methods=["get"])
    def group_chats(self, request):
        """Return only group chat rooms"""
        user = request.user
        rooms = Room.objects.filter(
            participants__user=user, is_group_chat=True
        ).order_by("-updated_at")
        serializer = self.get_serializer(rooms, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def direct_chats(self, request):
        """Return only direct (one-to-one) chat rooms"""
        user = request.user
        rooms = Room.objects.filter(
            participants__user=user, is_group_chat=False
        ).order_by("-updated_at")
        serializer = self.get_serializer(rooms, many=True)
        return Response(serializer.data)

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

    @action(detail=True, methods=["post"])
    def add_participants(self, request, pk=None):
        """Add multiple participants to an existing room"""
        room = self.get_object()
        user_ids = request.data.get("user_ids", [])

        if not user_ids:
            return Response(
                {"error": "No user IDs provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Add participants
        added_count = 0
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                _, created = Participant.objects.get_or_create(user=user, room=room)
                if created:
                    added_count += 1
            except User.DoesNotExist:
                pass

        # If this was a direct chat and we're adding more people, convert to group chat
        if not room.is_group_chat and room.participants.count() > 2:
            room.is_group_chat = True
            room.save()

        return Response(
            {
                "status": "success",
                "added_count": added_count,
                "is_group_chat": room.is_group_chat,
            }
        )


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
            .select_related("sender")
            .prefetch_related("receipts__recipient")
            .order_by("-sent_at")
        )

    def create(self, request, *args, **kwargs):
        room = get_object_or_404(Room, id=self.kwargs.get("room_pk"))

        # Check if user is participant in the room
        if not Participant.objects.filter(room=room, user=request.user).exists():
            return Response(
                {"error": "You are not a participant in this room"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data={**request.data, "room": room.id})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Get the full serialized message with receipt info
        result = MessageSerializer(serializer.instance).data

        return Response(result, status=status.HTTP_201_CREATED)


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
