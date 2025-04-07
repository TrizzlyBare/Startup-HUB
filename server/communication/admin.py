from django.contrib import admin
from .models import (
    Room,
    Participant,
    Message,
    CallLog,
    CallInvitation,
    WebRTCPeerConnection,
    WebRTCSession,
)


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


@admin.register(WebRTCSession)
class WebRTCSessionAdmin(admin.ModelAdmin):
    list_display = (
        "room",
        "session_type",
        "status",
        "initiator",
        "started_at",
        "ended_at",
    )
    list_filter = ("session_type", "status")
    search_fields = ("room__name", "initiator__username")


@admin.register(WebRTCPeerConnection)
class WebRTCPeerConnectionAdmin(admin.ModelAdmin):
    list_display = ("session", "local_user", "remote_user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("local_user__username", "remote_user__username")
