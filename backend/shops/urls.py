from rest_framework.routers import SimpleRouter

from shops.views.management import ShopViewSet
from shops.views.storefront import StorefrontViewSet

router = SimpleRouter(use_regex_path=False)
router.register("shop-storefronts", StorefrontViewSet, basename="storefront")
router.register("shops", ShopViewSet, basename="shop")

urlpatterns = router.urls
