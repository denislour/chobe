from rest_framework.routers import SimpleRouter

from listings.views.alerts import (
    NotificationPreferenceViewSet,
    NotificationViewSet,
)
from listings.views.management import ListingManagementViewSet

router = SimpleRouter(use_regex_path=False)
router.register("me/listings", ListingManagementViewSet, basename="my-listing")
router.register("me/notifications", NotificationViewSet, basename="notification")
router.register(
    "me/notification-preferences",
    NotificationPreferenceViewSet,
    basename="notification-preference",
)

urlpatterns = router.urls
