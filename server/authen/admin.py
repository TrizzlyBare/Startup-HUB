from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ContactLink, PastProject


class ContactLinkInline(admin.TabularInline):
    """Inline admin for contact links"""

    model = ContactLink
    extra = 1


class PastProjectInline(admin.TabularInline):
    """Inline admin for past projects"""

    model = PastProject
    extra = 1


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin view for extended user model
    """

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "industry",
        "is_staff",
        "is_active",
    )
    list_filter = ("industry", "is_staff", "is_active", "date_joined")
    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "skills",
        "industry",
        "career_summary",
    )
    ordering = ("username",)
    inlines = [ContactLinkInline, PastProjectInline]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal Info",
            {"fields": ("first_name", "last_name", "email", "profile_picture", "bio")},
        ),
        (
            "Professional Info",
            {"fields": ("industry", "experience", "skills", "career_summary")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                ),
            },
        ),
    )


@admin.register(ContactLink)
class ContactLinkAdmin(admin.ModelAdmin):
    """Admin configuration for contact links"""

    list_display = ("user", "title", "url")
    search_fields = ("user__username", "user__email", "title", "url")
    list_filter = ("title",)


@admin.register(PastProject)
class PastProjectAdmin(admin.ModelAdmin):
    """Admin configuration for past projects"""

    list_display = ("title", "user", "start_date", "end_date")
    list_filter = ("user__username", "start_date", "end_date")
    search_fields = ("title", "description", "technologies", "user__username")
    ordering = ("-end_date", "-start_date")
