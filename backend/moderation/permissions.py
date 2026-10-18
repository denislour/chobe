from rest_framework.permissions import BasePermission


class ModerationPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and request.user.is_active
            and request.user.is_staff
            and request.user.has_perm("listings.moderate_listing")
        )


class ReportReviewPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and request.user.is_active
            and request.user.is_staff
            and request.user.has_perm("moderation.review_report")
        )
