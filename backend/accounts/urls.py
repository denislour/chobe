from django.urls import include, path
from rest_framework.routers import SimpleRouter

from accounts.views.auth import AuthViewSet
from accounts.views.profile import ProfileViewSet
from accounts.views.privacy import AccountDataExportViewSet, PrivacyViewSet, ViewingHistoryViewSet

router = SimpleRouter()
router.register("auth", AuthViewSet, basename="auth")
router.register("me/data-exports", AccountDataExportViewSet, basename="data-export")
urlpatterns = [
    path("me/profile/", ProfileViewSet.as_view({"get": "retrieve", "patch": "partial_update"})),
    path("me/profile/avatar/", ProfileViewSet.as_view({"get": "avatar"}), name="profile-avatar"),
    path("me/privacy-settings/", PrivacyViewSet.as_view({"get": "retrieve", "patch": "partial_update"})),
    path("me/viewing-history/", ViewingHistoryViewSet.as_view({"get": "list", "post": "create", "delete": "clear"})),
    path("", include(router.urls)),
]
