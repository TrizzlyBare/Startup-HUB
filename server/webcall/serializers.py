from rest_framework import serializers
from .models import Room, Participant


class RoomSerializer(serializers.ModelSerializer):
    participants_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ["id", "name", "created_at", "participants_count"]
        read_only_fields = ["id", "created_at"]

    def get_participants_count(self, obj):
        return obj.participants.count()


class ParticipantSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Participant
        fields = ["id", "username", "joined_at"]
        read_only_fields = ["joined_at"]
