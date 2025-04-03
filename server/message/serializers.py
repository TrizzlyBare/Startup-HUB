from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Room, Message, Participant, MessageReceipt
from django.db import transaction

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

    class Meta:
        model = Participant
        fields = ["id", "user", "room", "joined_at", "last_read", "unread_count"]
        read_only_fields = ["joined_at", "last_read"]

    def get_unread_count(self, obj):
        return obj.unread_messages_count()


class RoomSerializer(serializers.ModelSerializer):
    participants = ParticipantSerializer(many=True, read_only=True)
    latest_message = serializers.SerializerMethodField()

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
