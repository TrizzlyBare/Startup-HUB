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
from django.utils import timezone
import uuid


class WebRTCSession(models.Model):
    """
    Represents a WebRTC peer connection session
    """

    SESSION_TYPES = (
        ("audio", "Audio"),
        ("video", "Video"),
        ("screen_share", "Screen Share"),
    )

    SESSION_STATUSES = (
        ("initiated", "Initiated"),
        ("connecting", "Connecting"),
        ("connected", "Connected"),
        ("disconnected", "Disconnected"),
        ("failed", "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(
        "Room", on_delete=models.CASCADE, related_name="webrtc_sessions"
    )
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES)
    status = models.CharField(
        max_length=20, choices=SESSION_STATUSES, default="initiated"
    )
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="initiated_webrtc_sessions",
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="webrtc_sessions"
    )

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    ice_config = models.JSONField(null=True, blank=True)
    media_constraints = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "WebRTC Session"
        verbose_name_plural = "WebRTC Sessions"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.session_type} session in {self.room.name}"

    def end_session(self):
        """
        End the current WebRTC session
        """
        self.status = "disconnected"
        self.ended_at = timezone.now()
        self.save(update_fields=["status", "ended_at"])

    def update_status(self, new_status):
        """
        Update session status with validation
        """
        if new_status in dict(self.SESSION_STATUSES):
            self.status = new_status
            self.save(update_fields=["status"])
        else:
            raise ValueError(f"Invalid session status: {new_status}")


class WebRTCPeerConnection(models.Model):
    """
    Represents individual peer connections within a WebRTC session
    """

    PEER_STATUSES = (
        ("pending", "Pending"),
        ("negotiating", "Negotiating"),
        ("connected", "Connected"),
        ("disconnected", "Disconnected"),
        ("failed", "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        WebRTCSession, on_delete=models.CASCADE, related_name="peer_connections"
    )
    local_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="local_peer_connections",
    )
    remote_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="remote_peer_connections",
    )

    status = models.CharField(max_length=20, choices=PEER_STATUSES, default="pending")

    connection_offer = models.TextField(null=True, blank=True)
    connection_answer = models.TextField(null=True, blank=True)

    ice_candidates = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("session", "local_user", "remote_user")
        verbose_name = "WebRTC Peer Connection"
        verbose_name_plural = "WebRTC Peer Connections"

    def __str__(self):
        return f"Peer Connection: {self.local_user} to {self.remote_user}"

    def update_connection_status(self, status, offer=None, answer=None):
        """
        Update peer connection status and optionally store offer/answer
        """
        if status in dict(self.PEER_STATUSES):
            self.status = status
            if offer:
                self.connection_offer = offer
            if answer:
                self.connection_answer = answer
            self.save()
        else:
            raise ValueError(f"Invalid peer connection status: {status}")

    def add_ice_candidate(self, candidate):
        """
        Add ICE candidate to the connection
        """
        if not self.ice_candidates:
            self.ice_candidates = []

        self.ice_candidates.append(candidate)
        self.save(update_fields=["ice_candidates"])
