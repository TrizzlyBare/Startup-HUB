from django.contrib import admin
from .models import Match, Like, Dislike


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("user", "matched_user", "created_at", "is_mutual")
    list_filter = ("is_mutual", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "matched_user__username",
        "matched_user__email",
    )
    date_hierarchy = "created_at"


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "liked_user", "created_at")
    list_filter = ("created_at",)
    search_fields = (
        "user__username",
        "user__email",
        "liked_user__username",
        "liked_user__email",
    )
    date_hierarchy = "created_at"


@admin.register(Dislike)
class DislikeAdmin(admin.ModelAdmin):
    list_display = ("user", "disliked_user", "created_at")
    list_filter = ("created_at",)
    search_fields = (
        "user__username",
        "user__email",
        "disliked_user__username",
        "disliked_user__email",
    )
    date_hierarchy = "created_at"
