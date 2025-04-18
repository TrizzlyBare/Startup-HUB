from django.contrib import admin
from .models import Room, Participant, Message, CallLog, CallInvitation


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "room_type", "created_at", "is_active")
    list_filter = ("room_type", "is_active")
    search_fields = ("name",)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("user", "room", "joined_at", "is_admin")
    list_filter = ("is_admin",)
    search_fields = ("user__username", "room__name")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "room", "message_type", "sent_at")
    list_filter = ("message_type", "sent_at")
    search_fields = ("content",)


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ("caller", "receiver", "call_type", "start_time", "status")
    list_filter = ("call_type", "status", "start_time")


@admin.register(CallInvitation)
class CallInvitationAdmin(admin.ModelAdmin):
    list_display = ("inviter", "invitee", "room", "call_type", "created_at", "status")
    list_filter = ("call_type", "status", "created_at")
    search_fields = ("inviter__username", "invitee__username")


# Add to admin.py to register the IncomingCallNotification model

from django.contrib import admin
from .models import (
    Room,
    Participant,
    Message,
    CallLog,
    CallInvitation,
    IncomingCallNotification,
)

# Keep existing admin registrations


@admin.register(IncomingCallNotification)
class IncomingCallNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "caller",
        "recipient",
        "call_type",
        "created_at",
        "expires_at",
        "status",
    )
    list_filter = ("call_type", "status", "created_at")
    search_fields = ("caller__username", "recipient__username")
    date_hierarchy = "created_at"
