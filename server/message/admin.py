from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Room, Message, Participant, MessageReceipt


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    readonly_fields = ["joined_at", "last_read"]
    raw_id_fields = ["user"]


class MessageReceiptInline(admin.TabularInline):
    model = MessageReceipt
    extra = 0
    readonly_fields = ["read_at"]
    raw_id_fields = ["recipient"]


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["sent_at"]
    raw_id_fields = ["sender"]
    fields = ["content", "sender", "sent_at"]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "id",
        "is_group_chat",
        "created_at",
        "updated_at",
        "participant_count",
        "message_count",
    ]
    list_filter = ["created_at", "updated_at", "is_group_chat"]
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
        "sent_at",
        "receipt_count",
        "read_count",
    ]
    list_filter = ["sent_at", "room__is_group_chat"]
    search_fields = ["content", "sender__username", "room__name"]
    readonly_fields = ["sent_at"]
    raw_id_fields = ["sender", "room"]
    inlines = [MessageReceiptInline]

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

    def receipt_count(self, obj):
        return obj.receipts.count()

    receipt_count.short_description = "Recipients"

    def read_count(self, obj):
        return obj.receipts.filter(is_read=True).count()

    read_count.short_description = "Read by"


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
    list_filter = ["joined_at", "last_read", "room__is_group_chat"]
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


@admin.register(MessageReceipt)
class MessageReceiptAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "message_content",
        "recipient_link",
        "is_read",
        "read_at",
    ]
    list_filter = ["is_read", "read_at"]
    search_fields = ["message__content", "recipient__username"]
    readonly_fields = ["read_at"]
    raw_id_fields = ["message", "recipient"]

    def message_content(self, obj):
        content = obj.message.content
        return (content[:40] + "...") if len(content) > 40 else content

    message_content.short_description = "Message"

    def recipient_link(self, obj):
        url = reverse("admin:auth_user_change", args=[obj.recipient.id])
        return format_html('<a href="{}">{}</a>', url, obj.recipient.username)

    recipient_link.short_description = "Recipient"
