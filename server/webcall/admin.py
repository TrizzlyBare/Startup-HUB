from django.contrib import admin
from .models import Room, Participant


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'joined_at')
    list_filter = ('joined_at',)
    search_fields = ('user__username', 'room__name')
    readonly_fields = ('joined_at',)
    date_hierarchy = 'joined_at'
