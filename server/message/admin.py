from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Room, Message, Participant


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    readonly_fields = ["joined_at", "last_read"]
    raw_id_fields = ["user"]


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["sent_at"]
    raw_id_fields = ["sender", "receiver"]
    fields = ["content", "sender", "receiver", "sent_at", "is_read"]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "id",
        "created_at",
        "updated_at",
        "participant_count",
        "message_count",
    ]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["name", "participants__user__username"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ParticipantInline, MessageInline]

    def participant_count(self, obj):
        return obj.participants.count()

    participant_count.short_description = "Participants"

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = "Messages"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "truncated_content",
        "room_link",
        "sender_link",
        "receiver_link",
        "sent_at",
        "is_read",
    ]
    list_filter = ["sent_at", "is_read"]
    search_fields = ["content", "sender__username", "receiver__username", "room__name"]
    readonly_fields = ["sent_at"]
    raw_id_fields = ["sender", "receiver", "room"]

    def truncated_content(self, obj):
        return (obj.content[:50] + "...") if len(obj.content) > 50 else obj.content

    truncated_content.short_description = "Content"

    def room_link(self, obj):
        url = reverse("admin:chat_room_change", args=[obj.room.id])
        return format_html('<a href="{}">{}</a>', url, obj.room.name)

    room_link.short_description = "Room"

    def sender_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.sender.id])
        return format_html('<a href="{}">{}</a>', url, obj.sender.username)

    sender_link.short_description = "Sender"

    def receiver_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.receiver.id])
        return format_html('<a href="{}">{}</a>', url, obj.receiver.username)

    receiver_link.short_description = "Receiver"


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user_link",
        "room_link",
        "joined_at",
        "last_read",
        "unread_count",
    ]
    list_filter = ["joined_at", "last_read"]
    search_fields = ["user__username", "room__name"]
    readonly_fields = ["joined_at", "last_read"]
    raw_id_fields = ["user", "room"]

    def user_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    user_link.short_description = "User"

    def room_link(self, obj):
        url = reverse("admin:chat_room_change", args=[obj.room.id])
        return format_html('<a href="{}">{}</a>', url, obj.room.name)

    room_link.short_description = "Room"

    def unread_count(self, obj):
        return obj.unread_messages_count()

    unread_count.short_description = "Unread Messages"
