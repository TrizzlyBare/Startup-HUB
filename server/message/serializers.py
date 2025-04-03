from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Room, Message, Participant, MessageReceipt
from django.db import transaction
from django.db.models import Count, Q

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class MessageReceiptSerializer(serializers.ModelSerializer):
    recipient_username = serializers.CharField(
        source="recipient.username", read_only=True
    )

    class Meta:
        model = MessageReceipt
        fields = ["id", "recipient", "recipient_username", "is_read", "read_at"]
        read_only_fields = ["id", "read_at"]


class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)
    receipts = MessageReceiptSerializer(many=True, read_only=True)
    read_status = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "content",
            "sender",
            "sender_username",
            "sent_at",
            "receipts",
            "read_status",
        ]
        read_only_fields = ["id", "sent_at"]

    def get_read_status(self, obj):
        """Provide a summary of read status (for convenient display)"""
        total = obj.receipts.count()
        read = obj.receipts.filter(is_read=True).count()
        return {"total": total, "read": read, "unread": total - read}


class ParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_active_status = serializers.SerializerMethodField()

    class Meta:
        model = Participant
        fields = [
            "id",
            "user",
            "room",
            "joined_at",
            "last_read",
            "unread_count",
            "last_active_status",
            "last_active",
        ]
        read_only_fields = ["joined_at", "last_read", "last_active"]

    def get_unread_count(self, obj):
        return obj.unread_messages_count()

    def get_last_active_status(self, obj):
        """Determine if user is online based on last_active timestamp"""
        from django.utils import timezone

        if not obj.last_active:
            return "offline"

        five_min_ago = timezone.now() - timezone.timedelta(minutes=5)
        return "online" if obj.last_active >= five_min_ago else "offline"


class RoomListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for room listings"""

    unread_count = serializers.IntegerField(read_only=True)
    latest_message_preview = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "id",
            "name",
            "updated_at",
            "is_group_chat",
            "unread_count",
            "latest_message_preview",
            "other_participant",
        ]

    def get_latest_message_preview(self, obj):
        """Get preview of the latest message"""
        latest_message = Message.objects.filter(room=obj).order_by("-sent_at").first()
        if not latest_message:
            return None

        return {
            "content": latest_message.content[:100]
            + ("..." if len(latest_message.content) > 100 else ""),
            "sender_username": latest_message.sender.username,
            "sent_at": latest_message.sent_at,
        }

    def get_other_participant(self, obj):
        """For direct chats, get the other participant"""
        if obj.is_group_chat:
            return None

        request = self.context.get("request")
        if not request or not request.user:
            return None

        other = Participant.objects.filter(room=obj).exclude(user=request.user).first()
        if not other:
            return None

        return {"user_id": str(other.user.id), "username": other.user.username}


class RoomSerializer(serializers.ModelSerializer):
    participants = ParticipantSerializer(many=True, read_only=True)
    latest_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Room
        fields = [
            "id",
            "name",
            "created_at",
            "updated_at",
            "is_group_chat",
            "participants",
            "latest_message",
            "unread_count",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_latest_message(self, obj):
        latest_message = Message.objects.filter(room=obj).order_by("-sent_at").first()
        if latest_message:
            return MessageSerializer(latest_message).data
        return None


class RoomCreateSerializer(serializers.ModelSerializer):
    participants = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    is_group_chat = serializers.BooleanField(default=False)

    class Meta:
        model = Room
        fields = ["name", "participants", "is_group_chat"]

    def create(self, validated_data):
        participants = validated_data.pop("participants", [])

        # Add current user to participants if not already included
        current_user_id = self.context["request"].user.id
        if current_user_id not in participants:
            participants.append(current_user_id)

        # Force is_group_chat to true if there are more than 2 participants
        if len(participants) > 2:
            validated_data["is_group_chat"] = True

        room = Room.objects.create(**validated_data)

        # Add participants to the room
        for user_id in participants:
            try:
                user = User.objects.get(id=user_id)
                Participant.objects.create(user=user, room=room)
            except User.DoesNotExist:
                pass

        return room


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["room", "content"]

    @transaction.atomic
    def create(self, validated_data):
        sender = self.context["request"].user
        room = validated_data.get("room")

        # Create the message
        message = Message.objects.create(sender=sender, **validated_data)

        # Create receipt records for all participants except sender
        participants = Participant.objects.filter(room=room).exclude(user=sender)
        receipts = [
            MessageReceipt(message=message, recipient=participant.user)
            for participant in participants
        ]

        if receipts:
            MessageReceipt.objects.bulk_create(receipts)

        # Update room timestamp
        room.save()  # This updates the 'updated_at' field

        return message
