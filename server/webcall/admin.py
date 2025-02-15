from django.contrib import admin
from .models import Room, Participant


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
    list_filter = ("created_at",)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("user", "room", "joined_at")
    list_filter = ("room", "joined_at")
    search_fields = ("user__username", "room__name")
