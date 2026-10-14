from django.contrib import admin

from accounts.models import (
    AccountDataExport,
    ConsentEvent,
    DeletionRequest,
    PrivacySettings,
    Profile,
    User,
    ViewingHistory,
)
from backoffice.admin import ModelAdmin
from backoffice.admin import UserAdmin as ThemedUserAdmin


@admin.register(User)
class UserAdmin(ThemedUserAdmin):
    pass


@admin.register(
    Profile,
    PrivacySettings,
    ConsentEvent,
    ViewingHistory,
    AccountDataExport,
    DeletionRequest,
)
class AccountDataAdmin(ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
