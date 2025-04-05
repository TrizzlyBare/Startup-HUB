from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, NoReverseMatch
from .models import Channel, Message
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


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "description")
    date_hierarchy = "created_at"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "sender",
        "channel",
        "created_at",
        "content",
        "is_unsent",
        "is_pinned",
    )
    list_filter = ("created_at", "is_unsent", "is_pinned")
    search_fields = ("content", "sender__username", "channel__name")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    raw_id_fields = ["sender", "channel"]

    def truncated_content(self, obj):
        return (obj.content[:50] + "...") if len(obj.content) > 50 else obj.content

    truncated_content.short_description = "Content"

    def channel_link(self, obj):
        try:
            url = reverse(
                f"admin:{obj.channel._meta.app_label}_{obj.channel._meta.model_name}_change",
                args=[obj.channel.id],
            )
            return format_html('<a href="{}">{}</a>', url, obj.channel.name)
        except NoReverseMatch:
            return obj.channel.name

    channel_link.short_description = "Channel"

    def sender_link(self, obj):
        return get_user_admin_link(obj.sender.id, obj.sender.username)

    sender_link.short_description = "Sender"
