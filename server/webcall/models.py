from django.db import models
import uuid
from django.conf import settings
from django.utils import timezone


class Room(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    max_participants = models.IntegerField(default=10)
    is_recording_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.id})"


class Participant(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="participants"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(default=timezone.now, null=True, blank=True)
    is_audio_muted = models.BooleanField(default=False)
    is_video_muted = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "room")

    def __str__(self):
        return f"{self.user.username} in {self.room.name}"
