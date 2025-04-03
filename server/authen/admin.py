from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ContactLink


class ContactLinkInline(admin.TabularInline):
    model = ContactLink
    extra = 1


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
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
            {"fields": ("industry", "experience", "skills")},
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
    list_display = ("user", "title", "url")
    search_fields = ("user__username", "user__email", "title", "url")
    list_filter = ("title",)
