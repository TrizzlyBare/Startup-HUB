from django.contrib import admin
from .models import StartupIdea, StartupImage
from django.utils.html import format_html


class StartupImageInline(admin.TabularInline):
    model = StartupImage
    extra = 1
    readonly_fields = ["created_at", "image_preview"]

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" />', obj.image.url)
        return "No image"

    image_preview.short_description = "Preview"


@admin.register(StartupIdea)
class StartupIdeaAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_user_username",
        "get_user_profile_picture",
        "stage",
        "user_role",
        "get_member_count",
        "created_at",
    )
    list_filter = ("stage", "user_role", "created_at")
    search_fields = (
        "name",
        "pitch",
        "description",
        "user__username",
        "user__email",
        "skills",
        "looking_for",
        "members__username",
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = [StartupImageInline]
    filter_horizontal = (
        "members",
    )  # Add a nice widget for managing many-to-many relationships

    fieldsets = (
        ("Basic Info", {"fields": ("user", "name", "stage", "user_role")}),
        ("Team", {"fields": ("members",)}),
        ("Details", {"fields": ("pitch", "description", "skills", "looking_for")}),
        ("Documents", {"fields": ("pitch_deck",)}),
        (
            "Links & Funding",
            {"fields": ("website", "funding_stage", "investment_needed")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_user_username(self, obj):
        return obj.user.username

    get_user_username.short_description = "Owner"
    get_user_username.admin_order_field = "user__username"

    def get_user_profile_picture(self, obj):
        if obj.user.profile_picture:
            return format_html(
                '<img src="{}" width="50" height="50" />', obj.user.profile_picture.url
            )
        return "No picture"

    get_user_profile_picture.short_description = "Profile Picture"

    def get_member_count(self, obj):
        return obj.member_count

    get_member_count.short_description = "Team Size"


@admin.register(StartupImage)
class StartupImageAdmin(admin.ModelAdmin):
    list_display = ("startup_idea", "caption", "image_preview", "created_at")
    list_filter = ("created_at",)
    search_fields = ("startup_idea__name", "caption")
    readonly_fields = ("created_at", "image_preview")

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" />', obj.image.url)
        return "No image"

    image_preview.short_description = "Image Preview"
