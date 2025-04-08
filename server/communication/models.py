from datetime import timedelta
from cloudinary.models import CloudinaryField
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
import cloudinary
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError


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
    profile_image = CloudinaryField("image", null=True, blank=True)

    def clean(self):
        """
        Validate that the UUID is correctly formatted
        """
        try:
            # Attempt to validate the UUID
            uuid.UUID(str(self.id))
        except ValueError:
            raise ValidationError({"id": "Invalid UUID format"})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Participant(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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

    def is_online(self):
        """
        Check if participant is currently online (active in the last 5 minutes)
        """
        if not self.last_active:
            return False
        return timezone.now() - self.last_active < timezone.timedelta(minutes=5)


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
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="read_messages", blank=True
    )

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
            ("initiated", "Initiated"),
            ("missed", "Missed"),
            ("answered", "Answered"),
            ("rejected", "Rejected"),
        ],
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Message in {self.room.name} by {self.sender.username}"

    def mark_as_read(self, user):
        """Mark message as read by a specific user"""
        if user != self.sender and user not in self.read_by.all():
            self.read_by.add(user)
            if self.read_by.count() == self.room.communication_participants.count() - 1:
                # Everyone except sender has read the message
                self.is_read = True
                self.save(update_fields=["is_read"])


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
            ("initiated", "Initiated"),
            ("missed", "Missed"),
            ("answered", "Answered"),
            ("rejected", "Rejected"),
        ],
    )

    def __str__(self):
        return f"Call from {self.caller.username} to {self.receiver.username}"

    def calculate_duration(self):
        """Calculate call duration if start and end times are available"""
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            self.duration = int(duration)
            self.save(update_fields=["duration"])


class MediaFile(models.Model):
    MEDIA_TYPES = (
        ("image", "Image"),
        ("video", "Video"),
        ("document", "Document"),
        ("audio", "Audio"),
    )

    name = models.CharField(max_length=255)
    file = CloudinaryField("auto", blank=True, null=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    public_id = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communication_media_files",
    )
    size = models.PositiveIntegerField(
        null=True, blank=True, validators=[MaxValueValidator(settings.MAX_UPLOAD_SIZE)]
    )
    file_extension = models.CharField(max_length=10, blank=True, null=True)

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

    def validate_file_extension(self):
        """Validate file extension against allowed types"""
        if self.file_extension:
            allowed_extensions = settings.ALLOWED_UPLOAD_EXTENSIONS.get(
                self.media_type, []
            )
            if self.file_extension.lower() not in allowed_extensions:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    f"File extension '{self.file_extension}' not allowed for {self.media_type}"
                )


class CallInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inviter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_call_invitations",
    )
    invitee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_call_invitations",
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    call_type = models.CharField(
        max_length=10, choices=[("audio", "Audio Call"), ("video", "Video Call")]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
            ("expired", "Expired"),
        ],
        default="pending",
    )

    def __str__(self):
        return f"Call invite from {self.inviter.username} to {self.invitee.username}"

    def is_expired(self):
        """Check if invitation has expired"""
        return timezone.now() > self.expires_at

    def auto_expire(self):
        """Mark invitation as expired if it's past the expiration time"""
        if self.is_expired() and self.status == "pending":
            self.status = "expired"
            self.save(update_fields=["status"])


from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone


class IncomingCallNotification(models.Model):
    """Model to track incoming call notifications"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_call_notifications",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_call_notifications",
    )
    room = models.ForeignKey("Room", on_delete=models.CASCADE)
    call_type = models.CharField(
        max_length=10, choices=[("audio", "Audio Call"), ("video", "Video Call")]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("seen", "Seen"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
            ("missed", "Missed"),
            ("expired", "Expired"),
        ],
        default="pending",
    )
    device_token = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Call from {self.caller.username} to {self.recipient.username}"

    # Update the IncomingCallNotification model methods

    def is_expired(self):
        """Check if notification has expired"""
        # Add some buffer time to account for processing delays
        buffer_seconds = 2
        return timezone.now() + timedelta(seconds=buffer_seconds) > self.expires_at

    def auto_expire(self):
        """Mark notification as expired if it's past the expiration time"""
        if self.is_expired() and self.status == "pending":
            self.status = "expired"
            self.save(update_fields=["status"])
            return True
        return False

    @classmethod
    def expire_outdated(cls):
        """Class method to expire all outdated notifications"""
        now = timezone.now()
        return cls.objects.filter(status="pending", expires_at__lte=now).update(
            status="expired"
        )

    @classmethod
    def get_active_for_user(cls, user):
        """Get active notifications for a user"""
        # First expire any outdated notifications
        cls.expire_outdated()

        # Then get active ones
        return cls.objects.filter(
            recipient=user,
            status__in=["pending", "seen"],
            expires_at__gt=timezone.now(),
        ).order_by("-created_at")
