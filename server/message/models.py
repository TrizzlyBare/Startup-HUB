from django.db import models
import uuid
from django.conf import settings
from django.utils import timezone


class Room(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_group_chat = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.id})"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages")
    content = models.TextField()
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return (
            f"Message from {self.sender.username} in {self.room.name} at {self.sent_at}"
        )


class MessageReceipt(models.Model):
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="receipts"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_receipts",
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("message", "recipient")

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class Participant(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_participants",
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
        current_time = timezone.now()
        self.last_read = current_time

        # Update all unread message receipts for this user in this room
        MessageReceipt.objects.filter(
            message__room=self.room, recipient=self.user, is_read=False
        ).update(is_read=True, read_at=current_time)

        self.save()

    def unread_messages_count(self):
        """Get count of unread messages for this participant."""
        return MessageReceipt.objects.filter(
            message__room=self.room, recipient=self.user, is_read=False
        ).count()

    def get_recent_messages(self, limit=50):
        """Get recent messages from the room."""
        return Message.objects.filter(room=self.room).order_by("-sent_at")[:limit]
