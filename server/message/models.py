from django.db import models
import uuid
from django.conf import settings
from django.utils import timezone


class Room(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.id})"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    content = models.TextField()
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_messages",
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username} at {self.sent_at}"


class Participant(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_participants",  # Changed this to avoid the clash
    )
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="participants"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "room")

    def __str__(self):
        return f"{self.user.username} in {self.room.name}"

    def mark_messages_as_read(self):
        """Mark all messages in the room as read up to current time."""
        self.last_read = timezone.now()
        Message.objects.filter(
            room=self.room,
            sent_at__lte=self.last_read,
            receiver=self.user,
            is_read=False,
        ).update(is_read=True)
        self.save()

    def unread_messages_count(self):
        """Get count of unread messages for this participant."""
        return Message.objects.filter(
            room=self.room,
            receiver=self.user,
            sent_at__gt=self.last_read,
            is_read=False,
        ).count()

    def get_recent_messages(self, limit=50):
        """Get recent messages from the room."""
        return Message.objects.filter(room=self.room).order_by("-sent_at")[:limit]
