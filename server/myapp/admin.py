from django.contrib import admin
# Import your models here when you create them
# from .models import YourModel
from .models import StartupProfile, StartupImage
from django.utils.html import format_html

# Register your models when you create them
# @admin.register(YourModel)
# class YourModelAdmin(admin.ModelAdmin):
#     list_display = ('field1', 'field2')
#     list_filter = ('field1',)
#     search_fields = ('field1', 'field2')

class StartupImageInline(admin.TabularInline):
    model = StartupImage
    extra = 1
    readonly_fields = ['created_at']

@admin.register(StartupProfile)
class StartupProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_user_profile_picture', 'startup_name', 'role', 'startup_stage', 'created_at')
    list_filter = ('role', 'startup_stage', 'created_at')
    search_fields = ('user__username', 'startup_name', 'pitch', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [StartupImageInline]
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'bio', 'age', 'location', 'interests', 'profile_images')
        }),
        ('Startup Details', {
            'fields': ('startup_name', 'startup_stage', 'pitch', 'description')
        }),
        ('Role & Skills', {
            'fields': ('role', 'skills', 'looking_for')
        }),
        ('Documents & Media', {
            'fields': ('pitch_deck', 'startup_images')
        }),
        ('Links', {
            'fields': ('website', 'linkedin', 'github')
        }),
        ('Funding', {
            'fields': ('funding_stage', 'investment_needed')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_user_profile_picture(self, obj):
        if obj.user.profile_picture:
            return format_html('<img src="{}" width="50" height="50" />', obj.user.profile_picture.url)
        return "No picture"
    get_user_profile_picture.short_description = 'Profile Picture'
