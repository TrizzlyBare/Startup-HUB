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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communication_participants",
    )
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="communication_participants"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "room")

    def __str__(self):
        return f"{self.user.username} in {self.room.name}"


class MediaFile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webcall_media_files",
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="media_files")
    file = models.FileField(upload_to="media_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(max_length=50, blank=True, null=True)
    file_size = models.PositiveIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    is_shared = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
