from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import (
    Q,
    Count,
    Exists,
    OuterRef,
    F,
    Sum,
    Case,
    When,
    IntegerField,
)
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model

from .models import Room, Message, Participant, MessageReceipt
from .serializers import (
    RoomSerializer,
    RoomCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    ParticipantSerializer,
    RoomListSerializer,
)

User = get_user_model()


class RoomViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return RoomCreateSerializer
        elif (
            self.action == "list"
            or self.action == "group_chats"
            or self.action == "direct_chats"
        ):
            return RoomListSerializer
        return RoomSerializer

    def get_queryset(self):
        user = self.request.user
        # Include unread message count in queryset
        return (
            Room.objects.filter(participants__user=user)
            .annotate(
                unread_count=Count(
                    "messages__receipts",
                    filter=Q(
                        messages__receipts__recipient=user,
                        messages__receipts__is_read=False,
                    ),
                )
            )
            .order_by("-updated_at")
        )

    @action(detail=False, methods=["get"])
    def group_chats(self, request):
        user = request.user
        rooms = (
            Room.objects.filter(participants__user=user, is_group_chat=True)
            .annotate(
                unread_count=Count(
                    "messages__receipts",
                    filter=Q(
                        messages__receipts__recipient=user,
                        messages__receipts__is_read=False,
                    ),
                )
            )
            .order_by("-updated_at")
        )
        serializer = self.get_serializer(rooms, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def direct_chats(self, request):
        """Return only direct (one-to-one) chat rooms"""
        user = request.user
        rooms = (
            Room.objects.filter(participants__user=user, is_group_chat=False)
            .annotate(
                unread_count=Count(
                    "messages__receipts",
                    filter=Q(
                        messages__receipts__recipient=user,
                        messages__receipts__is_read=False,
                    ),
                )
            )
            .order_by("-updated_at")
        )
        serializer = self.get_serializer(rooms, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        room = self.get_object()
        user = request.user

        if not Participant.objects.filter(room=room, user=user).exists():
            participant = Participant.objects.create(room=room, user=user)

            # Notify other participants about the new member
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{room.id}",
                {
                    "type": "notification",
                    "message": "New participant joined",
                    "data": {
                        "room_id": str(room.id),
                        "user_id": str(user.id),
                        "username": user.username,
                        "action": "joined",
                    },
                },
            )

            return Response({"status": "joined"})
        return Response({"status": "already joined"})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        room = self.get_object()
        user = request.user

        participant = Participant.objects.filter(room=room, user=user).first()
        if participant:
            participant.delete()

            # Notify other participants
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{room.id}",
                {
                    "type": "notification",
                    "message": "Participant left",
                    "data": {
                        "room_id": str(room.id),
                        "user_id": str(user.id),
                        "username": user.username,
                        "action": "left",
                    },
                },
            )

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
        added_users = []
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                _, created = Participant.objects.get_or_create(user=user, room=room)
                if created:
                    added_count += 1
                    added_users.append(
                        {"user_id": str(user.id), "username": user.username}
                    )
            except User.DoesNotExist:
                pass

        # If this was a direct chat and we're adding more people, convert to group chat
        if not room.is_group_chat and room.participants.count() > 2:
            room.is_group_chat = True
            room.save()

        # Notify existing participants
        if added_count > 0:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{room.id}",
                {
                    "type": "notification",
                    "message": "New participants added",
                    "data": {
                        "room_id": str(room.id),
                        "added_by": request.user.username,
                        "users": added_users,
                        "is_group_chat": room.is_group_chat,
                    },
                },
            )

        return Response(
            {
                "status": "success",
                "added_count": added_count,
                "is_group_chat": room.is_group_chat,
                "added_users": added_users,
            }
        )

    @action(detail=True, methods=["get"])
    def online_participants(self, request, pk=None):
        """Get online participants in a room"""
        room = self.get_object()

        # Users active in the last 5 minutes are considered online
        five_min_ago = timezone.now() - timezone.timedelta(minutes=5)
        participants = Participant.objects.filter(
            room=room, last_active__gte=five_min_ago
        ).select_related("user")

        data = [
            {
                "user_id": str(participant.user.id),
                "username": participant.user.username,
                "last_active": participant.last_active,
            }
            for participant in participants
        ]

        return Response(data)

    @action(detail=False, methods=["get"])
    def unread_counts(self, request):
        """Get unread message counts for all rooms of the current user"""
        user = request.user

        rooms = Room.objects.filter(participants__user=user).annotate(
            unread_count=Count(
                "messages__receipts",
                filter=Q(
                    messages__receipts__recipient=user,
                    messages__receipts__is_read=False,
                ),
            )
        )

        data = {
            "rooms": [
                {
                    "room_id": str(room.id),
                    "unread_count": room.unread_count,
                    "name": room.name,
                    "is_group_chat": room.is_group_chat,
                }
                for room in rooms
            ],
            "total_unread": sum(room.unread_count for room in rooms),
        }

        return Response(data)


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
        message = serializer.save()

        # Get the full serialized message with receipt info
        result = MessageSerializer(message).data

        # Send real-time notification via Redis
        channel_layer = get_channel_layer()

        # Notify room participants through WebSockets
        message_data = {
            "id": str(message.id),
            "content": message.content,
            "sender_id": str(message.sender.id),
            "sender_username": message.sender.username,
            "sent_at": message.sent_at.isoformat(),
            # Include receipt info from result
            "receipts": result.get("receipts", []),
            "read_status": result.get("read_status", {}),
        }

        # Send to room group
        async_to_sync(channel_layer.group_send)(
            f"chat_{room.id}", {"type": "chat.message", "message": message_data}
        )

        # Also send individual notifications to participants who aren't in the room
        participants = Participant.objects.filter(room=room).exclude(user=request.user)
        for participant in participants:
            async_to_sync(channel_layer.group_send)(
                f"user_{participant.user.id}",
                {
                    "type": "notification",
                    "message": "New message",
                    "data": {
                        "room_id": str(room.id),
                        "sender": request.user.username,
                        "message_preview": message.content[:50]
                        + ("..." if len(message.content) > 50 else ""),
                    },
                },
            )

        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def history(self, request, room_pk=None):
        """Get paginated chat history"""
        # Check if user is participant in the room
        if not Participant.objects.filter(room_id=room_pk, user=request.user).exists():
            return Response(
                {"error": "You are not a participant in this room"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get query parameters
        before_timestamp = request.query_params.get("before")
        limit = int(request.query_params.get("limit", 20))

        # Base query
        query = Message.objects.filter(room_id=room_pk)

        # Filter messages before the given timestamp
        if before_timestamp:
            try:
                before_time = timezone.datetime.fromisoformat(before_timestamp)
                query = query.filter(sent_at__lt=before_time)
            except (ValueError, TypeError):
                pass

        # Get paginated results
        messages = (
            query.select_related("sender")
            .prefetch_related("receipts__recipient")
            .order_by("-sent_at")[:limit]
        )

        serializer = MessageSerializer(messages, many=True)

        return Response(
            {"messages": serializer.data, "has_more": messages.count() == limit}
        )


class ParticipantViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantSerializer

    def get_queryset(self):
        room_id = self.kwargs.get("room_pk")
        return Participant.objects.filter(room_id=room_id).select_related("user")

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None, room_pk=None):
        participant = self.get_object()

        # Only allow users to mark their own messages as read
        if participant.user != request.user:
            return Response(
                {"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN
            )

        participant.mark_messages_as_read()

        # Notify other participants through WebSockets
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{room_pk}",
            {
                "type": "read.status",
                "user_id": str(request.user.id),
                "username": request.user.username,
                "timestamp": timezone.now().isoformat(),
            },
        )

        return Response({"status": "marked as read"})

    @action(detail=False, methods=["post"])
    def typing(self, request, room_pk=None):
        """Update typing status"""
        is_typing = request.data.get("is_typing", False)

        # Check if user is participant
        if not Participant.objects.filter(room_id=room_pk, user=request.user).exists():
            return Response(
                {"error": "You are not a participant in this room"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Update typing status via Redis
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{room_pk}",
            {
                "type": "typing.status",
                "user_id": str(request.user.id),
                "username": request.user.username,
                "is_typing": is_typing,
            },
        )

        # If typing, store status with expiration
        if is_typing:
            typing_channel = f"typing:{room_pk}:{request.user.id}"
            async_to_sync(channel_layer.send)(
                typing_channel, {"type": "typing_indicator", "is_typing": True}
            )

        return Response({"status": "typing status updated"})
