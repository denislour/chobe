from rest_framework.routers import SimpleRouter

from listings.views.alerts import (
    NotificationPreferenceViewSet,
    NotificationViewSet,
)
from listings.views.management import ListingManagementViewSet
from listings.views.reports import ReportManagementViewSet, ReportViewSet

router = SimpleRouter(use_regex_path=False)
router.register("me/listings", ListingManagementViewSet, basename="my-listing")
router.register("me/notifications", NotificationViewSet, basename="notification")
router.register(
    "me/notification-preferences",
    NotificationPreferenceViewSet,
    basename="notification-preference",
)
router.register("me/reports", ReportViewSet, basename="report")
router.register("admin/reports", ReportManagementViewSet, basename="report-management")

urlpatterns = router.urls
