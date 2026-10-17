from rest_framework.routers import SimpleRouter

from listings.views.management import ListingManagementViewSet
from listings.views.moderation import ModerationViewSet
from listings.views.discovery import ListingViewSet, HomeViewSet, FavoriteViewSet
from listings.views.alerts import SavedSearchViewSet, NotificationPreferenceViewSet, NotificationViewSet

router = SimpleRouter(use_regex_path=False)
router.register("me/listings", ListingManagementViewSet, basename="my-listing")
router.register("admin/moderation", ModerationViewSet, basename="moderation")
router.register("listings", ListingViewSet, basename="listing")
router.register("home", HomeViewSet, basename="home")
router.register("me/favorites", FavoriteViewSet, basename="favorite")
router.register("me/saved-searches", SavedSearchViewSet, basename="saved-search")
router.register("me/notification-preferences", NotificationPreferenceViewSet, basename="notification-preference")
router.register("me/notifications", NotificationViewSet, basename="notification")
urlpatterns = router.urls
