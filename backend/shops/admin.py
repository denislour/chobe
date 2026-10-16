from django.contrib import admin, messages
from rest_framework.exceptions import ValidationError

from backoffice.admin import ModelAdmin
from shops.models import Shop, ShopAuditEvent, ShopSlug
from shops.services.moderation import moderate_shop


@admin.register(Shop)
class ShopAdmin(ModelAdmin):
    list_display = ("name", "slug", "owner", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "slug", "owner__username")
    actions = ("suspend_shops", "restore_shops")
    readonly_fields = tuple(field.name for field in Shop._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Suspend selected shops", permissions=("change",))
    def suspend_shops(self, request, queryset):
        self.moderate_selection(request, queryset, suspend=True)

    @admin.action(
        description="Restore selected suspended shops", permissions=("change",)
    )
    def restore_shops(self, request, queryset):
        self.moderate_selection(request, queryset, suspend=False)

    def moderate_selection(self, request, queryset, *, suspend):
        for shop in queryset:
            try:
                moderate_shop(shop.pk, request.user, suspend=suspend)
            except ValidationError as error:
                self.message_user(
                    request, f"{shop.name}: {error.detail}", messages.ERROR
                )
            else:
                self.log_change(request, shop, "Shop suspension changed.")
                self.message_user(request, f"Updated {shop.name}.", messages.SUCCESS)


@admin.register(ShopSlug, ShopAuditEvent)
class ShopHistoryAdmin(ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
