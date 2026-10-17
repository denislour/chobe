from rest_framework.routers import SimpleRouter

from listings.views.management import ListingManagementViewSet
from listings.views.moderation import ModerationViewSet

router = SimpleRouter(use_regex_path=False)
router.register("me/listings", ListingManagementViewSet, basename="my-listing")
router.register("admin/moderation", ModerationViewSet, basename="moderation")
urlpatterns = router.urls
