from django.contrib import admin
from .models import StartupIdea, StartupImage
from django.utils.html import format_html


class StartupImageInline(admin.TabularInline):
    model = StartupImage
    extra = 1
    readonly_fields = ["created_at"]


@admin.register(StartupIdea)
class StartupIdeaAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_user_username",
        "get_user_profile_picture",
        "stage",
        "user_role",
        "created_at",
    )
    list_filter = ("stage", "user_role", "created_at")
    search_fields = ("name", "pitch", "description", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    inlines = [StartupImageInline]

    fieldsets = (
        ("Basic Info", {"fields": ("user", "name", "stage", "user_role")}),
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

    get_user_username.short_description = "Username"
    get_user_username.admin_order_field = "user__username"

    def get_user_profile_picture(self, obj):
        if obj.user.profile_picture:
            return format_html(
                '<img src="{}" width="50" height="50" />', obj.user.profile_picture.url
            )
        return "No picture"

    get_user_profile_picture.short_description = "Profile Picture"


@admin.register(StartupImage)
class StartupImageAdmin(admin.ModelAdmin):
    list_display = ("startup_idea", "caption", "created_at")
    list_filter = ("created_at",)
    search_fields = ("startup_idea__name", "caption")
    readonly_fields = ("created_at", "image_preview")

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="200" />', obj.image.url)
        return "No image"

    image_preview.short_description = "Image Preview"
