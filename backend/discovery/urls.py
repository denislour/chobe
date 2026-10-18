from rest_framework.routers import SimpleRouter

from discovery.views import HomeViewSet, ListingViewSet

router = SimpleRouter(use_regex_path=False)
router.register("listings", ListingViewSet, basename="listing")
router.register("home", HomeViewSet, basename="home")

urlpatterns = router.urls
