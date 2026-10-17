from rest_framework.routers import SimpleRouter

from listings.views.management import ListingManagementViewSet
from listings.views.moderation import ModerationViewSet
from listings.views.discovery import ListingViewSet, HomeViewSet

router = SimpleRouter(use_regex_path=False)
router.register("me/listings", ListingManagementViewSet, basename="my-listing")
router.register("admin/moderation", ModerationViewSet, basename="moderation")
router.register("listings", ListingViewSet, basename="listing")
router.register("home", HomeViewSet, basename="home")
urlpatterns = router.urls
