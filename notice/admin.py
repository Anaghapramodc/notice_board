from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import CustomUser, Notice

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'user_type', 'is_active')
    list_filter = ('user_type', 'is_active')
    search_fields = ('username', 'email')
    actions = ['approve_users']

    def approve_users(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "Selected users approved successfully")

    approve_users.short_description = "Approve selected users"


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('notice_subject', 'created_at')
