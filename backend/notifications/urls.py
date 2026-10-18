from rest_framework.routers import SimpleRouter

from notifications.views import NotificationPreferenceViewSet, NotificationViewSet

router = SimpleRouter(use_regex_path=False)
router.register("me/notifications", NotificationViewSet, basename="notification")
router.register(
    "me/notification-preferences",
    NotificationPreferenceViewSet,
    basename="notification-preference",
)

urlpatterns = router.urls
