from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from listings.models import Listing


@admin.register(Listing)
class ListingAdmin(ModelAdmin):
    list_display = ("id", "title", "status", "version", "retention_due_at", "workspace")
    list_filter = ("status",)
    search_fields = ("title",)
    readonly_fields = tuple(field.name for field in Listing._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Workspace")
    def workspace(self, obj):
        return format_html(
            '<a href="{}/admin/moderation">Review listings</a>', settings.FRONTEND_URL
        )
