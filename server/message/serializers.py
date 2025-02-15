from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Room, Message, Participant

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)
    receiver_username = serializers.CharField(
        source="receiver.username", read_only=True
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "content",
            "sender",
            "sender_username",
            "receiver",
            "receiver_username",
            "sent_at",
            "is_read",
        ]
        read_only_fields = ["id", "sent_at", "is_read"]


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

    class Meta:
        model = Room
        fields = ["name", "participants"]

    def create(self, validated_data):
        participants = validated_data.pop("participants", [])
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
        fields = ["room", "content", "receiver"]

    def create(self, validated_data):
        sender = self.context["request"].user
        message = Message.objects.create(sender=sender, **validated_data)
        return message
