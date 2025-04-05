from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ContactLink


class ContactLinkInline(admin.TabularInline):
    """Inline admin for contact links"""

    model = ContactLink
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
        "past_projects",
    )
    ordering = ("username",)
    inlines = [ContactLinkInline]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal Info",
            {"fields": ("first_name", "last_name", "email", "profile_picture", "bio")},
        ),
        (
            "Professional Info",
            {
                "fields": (
                    "industry",
                    "experience",
                    "skills",
                    "past_projects",
                    "career_summary",
                )
            },
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


# Only register ContactLink once
# There seems to be a duplicate registration somewhere
# Make sure ContactLink is only registered once in your code
@admin.register(ContactLink)
class ContactLinkAdmin(admin.ModelAdmin):
    """Admin configuration for contact links"""

    list_display = ("user", "title", "url")
    search_fields = ("user__username", "user__email", "title", "url")
    list_filter = ("title",)
