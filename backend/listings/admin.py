from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from listings.models import Listing, ModerationCase, Report


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


@admin.register(ModerationCase)
class ModerationCaseAdmin(ModelAdmin):
    list_display = ("id", "status", "source", "appeal_open", "updated_at")
    readonly_fields = tuple(field.name for field in ModerationCase._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Report)
class ReportAdmin(ModelAdmin):
    list_display = ("id", "reason", "status", "created_at")
    readonly_fields = tuple(field.name for field in Report._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
