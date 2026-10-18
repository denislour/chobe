from django.contrib import admin
from unfold.admin import ModelAdmin

from moderation.models import ModerationCase, Report


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
