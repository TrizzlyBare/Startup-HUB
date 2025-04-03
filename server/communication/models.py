from cloudinary.models import CloudinaryField
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class Room(models.Model):
    ROOM_TYPES = (
        ("direct", "Direct Message"),
        ("group", "Group Chat"),
        ("video", "Video Call"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default="direct")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    max_participants = models.IntegerField(default=10)
    profile_image = models.ImageField(upload_to="room_profiles/", null=True, blank=True)

    def __str__(self):
        return self.name


class Participant(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="participants"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "room")

    def __str__(self):
        return f"{self.user.username} in {self.room.name}"


class Message(models.Model):
    MESSAGE_TYPES = (
        ("text", "Text Message"),
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("call", "Call Notification"),
        ("location", "Location"),
        ("document", "Document"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(null=True, blank=True)
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPES, default="text"
    )

    image = CloudinaryField("image", null=True, blank=True)
    video = CloudinaryField("video", null=True, blank=True)
    audio = CloudinaryField("audio", null=True, blank=True)
    document = CloudinaryField("raw", null=True, blank=True)

    # Location fields
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    # Call-related fields
    call_duration = models.IntegerField(null=True, blank=True)
    call_type = models.CharField(
        max_length=10,
        choices=[("audio", "Audio Call"), ("video", "Video Call")],
        null=True,
        blank=True,
    )
    call_status = models.CharField(
        max_length=20,
        choices=[
            ("missed", "Missed"),
            ("answered", "Answered"),
            ("rejected", "Rejected"),
        ],
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Message in {self.room.name} by {self.sender.username}"


class CallLog(models.Model):
    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="outgoing_calls",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="incoming_calls",
    )
    call_type = models.CharField(
        max_length=10, choices=[("audio", "Audio Call"), ("video", "Video Call")]
    )
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # in seconds
    status = models.CharField(
        max_length=20,
        choices=[
            ("missed", "Missed"),
            ("answered", "Answered"),
            ("rejected", "Rejected"),
        ],
    )

    def __str__(self):
        return f"Call from {self.caller.username} to {self.receiver.username}"


class MediaFile(models.Model):
    MEDIA_TYPES = (("image", "Image"), ("video", "Video"), ("document", "Document"))

    name = models.CharField(max_length=255)
    file = CloudinaryField("auto", blank=True, null=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    public_id = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="uploaded_media"
    )

    def save(self, *args, **kwargs):
        # Extract public_id when saving
        if self.file:
            self.public_id = self.file.public_id
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Delete from Cloudinary when model instance is deleted
        from .utils import CloudinaryHelper

        if self.public_id:
            CloudinaryHelper.delete_resource(
                self.public_id, resource_type=self.media_type
            )

        super().delete(*args, **kwargs)
