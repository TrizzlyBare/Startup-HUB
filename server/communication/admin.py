from django.contrib import admin
from .models import Room, Participant, Message, CallLog


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
