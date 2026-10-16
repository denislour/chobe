from rest_framework.routers import SimpleRouter

from accounts.views.auth import AuthViewSet
from accounts.views.privacy import (
    AccountDataExportViewSet,
    DeletionStatusViewSet,
    DeletionViewSet,
    PrivacyViewSet,
    ViewingHistoryViewSet,
)
from accounts.views.profile import ProfileViewSet

router = SimpleRouter(use_regex_path=False)
router.register("auth", AuthViewSet, basename="auth")
router.register("me/data-exports", AccountDataExportViewSet, basename="data-export")
router.register("me/deletion-requests", DeletionViewSet, basename="deletion-request")
router.register(
    "account-deletion-status", DeletionStatusViewSet, basename="deletion-status"
)
router.register("profiles", ProfileViewSet, basename="profile")
router.register("privacy-settings", PrivacyViewSet, basename="privacy-settings")
router.register("me/viewing-history", ViewingHistoryViewSet, basename="viewing-history")

urlpatterns = router.urls
