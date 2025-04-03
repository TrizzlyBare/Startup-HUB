from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, NoReverseMatch
from .models import Room, Participant
from django.contrib.auth import get_user_model

User = get_user_model()


def get_user_admin_link(user_id, username):
    """Try to get a link to the user admin page, fallback to plain text if not possible"""
    try:
        # Try different possible URL patterns
        for pattern in [
            f"admin:{User._meta.app_label}_{User._meta.model_name}_change",
            "admin:auth_user_change",
            "admin:users_user_change",
            "admin:accounts_user_change",
            "admin:authen_customuser_change",
        ]:
            try:
                url = reverse(pattern, args=[user_id])
                return format_html('<a href="{}">{}</a>', url, username)
            except NoReverseMatch:
                continue
        return username
    except Exception:
        return username


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    readonly_fields = ["joined_at", "last_active"]
    fields = ["user", "joined_at", "last_active", "is_audio_muted", "is_video_muted"]
    raw_id_fields = ["user"]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_at",
        "updated_at",
        "is_active",
        "max_participants",
        "participant_count",
    )
    list_filter = ("is_active", "created_at", "is_recording_enabled")
    search_fields = ("name",)
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    inlines = [ParticipantInline]

    def participant_count(self, obj):
        return obj.participants.count()

    def active_participant_count(self, obj):
        from django.utils import timezone

        thirty_sec_ago = timezone.now() - timezone.timedelta(seconds=30)
        return obj.participants.filter(last_active__gte=thirty_sec_ago).count()

    participant_count.short_description = "Participants"
    active_participant_count.short_description = "Active Participants"


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "user_link",
        "room_link",
        "joined_at",
        "last_active",
        "is_active",
        # Replace these with actual fields or remove them
        "is_muted",
    )
    list_filter = (
        "joined_at",
        "last_active",
        # Replace these with actual fields or remove them
        "is_muted",
    )
    search_fields = ("user__username", "room__name")
    readonly_fields = ("joined_at", "last_active")
    date_hierarchy = "joined_at"
    raw_id_fields = ["user", "room"]

    def user_link(self, obj):
        # Implement or remove
        pass

    def room_link(self, obj):
        # Implement or remove
        pass

    def is_active(self, obj):
        from django.utils import timezone

        thirty_sec_ago = timezone.now() - timezone.timedelta(seconds=30)
        return obj.last_active and obj.last_active >= thirty_sec_ago

    is_active.boolean = True
