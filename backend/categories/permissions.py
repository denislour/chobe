from rest_framework.permissions import BasePermission


class TaxonomyPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated or not user.is_active or not user.is_staff:
            return False
        required = {
            "create": "add_category",
            "partial_update": "change_category",
            "publish": "publish_category",
            "retire": "retire_category",
        }.get(view.action, "view_category")
        return user.has_perm(f"categories.{required}")
