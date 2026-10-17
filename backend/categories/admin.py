from django.conf import settings
from django.contrib import admin

from backoffice.admin import ModelAdmin
from categories.models import Category, CategoryAuditEvent, CategoryRevision


@admin.register(Category, CategoryRevision, CategoryAuditEvent)
class TaxonomyAdmin(ModelAdmin):
    change_list_template = "admin/categories/change_list.html"

    def changelist_view(self, request, extra_context=None):
        context = dict(extra_context or {})
        context["taxonomy_workspace_url"] = (
            settings.FRONTEND_URL.rstrip("/") + "/admin/categories"
        )
        return super().changelist_view(request, extra_context=context)

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
