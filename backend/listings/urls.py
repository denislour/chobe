from rest_framework.routers import SimpleRouter

from listings.views.management import ListingManagementViewSet

router = SimpleRouter(use_regex_path=False)
router.register("me/listings", ListingManagementViewSet, basename="my-listing")

urlpatterns = router.urls
