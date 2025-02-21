from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, NoReverseMatch
from .models import Room, Message, Participant, MessageReceipt
from django.contrib.auth import get_user_model

User = get_user_model()


def get_user_admin_link(user_id, username):
    """Try to get a link to the user admin page, fallback to plain text if not possible"""
    try:
        # Try different possible URL patterns
        for pattern in [
            f"admin:{User._meta.app_label}_{User._meta.model_name}_change",
            "admin:auth_user_change",
            "admin:users_user_change",  # Common custom user app pattern
            "admin:accounts_user_change",  # Another common pattern
        ]:
            try:
                url = reverse(pattern, args=[user_id])
                return format_html('<a href="{}">{}</a>', url, username)
            except NoReverseMatch:
                continue
        # If no URL pattern works, just return the username
        return username
    except Exception:
        # Final fallback
        return username


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
    list_display = ('name', 'created_at', 'updated_at', 'is_group_chat')
    list_filter = ('is_group_chat', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [ParticipantInline, MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'room', 'sent_at', 'content')
    list_filter = ('sent_at', 'room')
    search_fields = ('content', 'sender__username', 'room__name')
    readonly_fields = ('sent_at',)
    date_hierarchy = 'sent_at'
    raw_id_fields = ["sender", "room"]
    inlines = [MessageReceiptInline]

    def truncated_content(self, obj):
        return (obj.content[:50] + "...") if len(obj.content) > 50 else obj.content

    truncated_content.short_description = "Content"

    def room_link(self, obj):
        try:
            url = reverse("admin:chat_room_change", args=[obj.room.id])
            return format_html('<a href="{}">{}</a>', url, obj.room.name)
        except NoReverseMatch:
            return obj.room.name

    room_link.short_description = "Room"

    def sender_link(self, obj):
        return get_user_admin_link(obj.sender.id, obj.sender.username)

    sender_link.short_description = "Sender"

    def receipt_count(self, obj):
        return obj.receipts.count()

    receipt_count.short_description = "Recipients"

    def read_count(self, obj):
        return obj.receipts.filter(is_read=True).count()

    read_count.short_description = "Read by"


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'joined_at', 'last_read')
    list_filter = ('joined_at', 'last_active')
    search_fields = ('user__username', 'room__name')
    readonly_fields = ('joined_at',)
    date_hierarchy = 'joined_at'
    raw_id_fields = ["user", "room"]

    def user_link(self, obj):
        return get_user_admin_link(obj.user.id, obj.user.username)

    user_link.short_description = "User"

    def room_link(self, obj):
        try:
            url = reverse("admin:chat_room_change", args=[obj.room.id])
            return format_html('<a href="{}">{}</a>', url, obj.room.name)
        except NoReverseMatch:
            return obj.room.name

    room_link.short_description = "Room"

    def unread_count(self, obj):
        return obj.unread_messages_count()

    unread_count.short_description = "Unread Messages"


@admin.register(MessageReceipt)
class MessageReceiptAdmin(admin.ModelAdmin):
    list_display = ('message', 'recipient', 'is_read', 'read_at')
    list_filter = ('is_read', 'read_at')
    search_fields = ('recipient__username', 'message__content')
    readonly_fields = ('read_at',)
    raw_id_fields = ["message", "recipient"]

    def message_content(self, obj):
        content = obj.message.content
        return (content[:40] + "...") if len(content) > 40 else content

    message_content.short_description = "Message"

    def recipient_link(self, obj):
        return get_user_admin_link(obj.recipient.id, obj.recipient.username)

    recipient_link.short_description = "Recipient"
