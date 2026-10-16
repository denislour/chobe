from rest_framework.routers import SimpleRouter

from shops.views.management import ShopViewSet

router = SimpleRouter(use_regex_path=False)
router.register("shops", ShopViewSet, basename="shop")

urlpatterns = router.urls
