from rest_framework.routers import SimpleRouter

from engagement.views.favorites import FavoriteViewSet
from engagement.views.following import FollowedShopsViewSet

router = SimpleRouter(use_regex_path=False)
router.register("me/favorites", FavoriteViewSet, basename="favorite")
router.register("me/followed-shops", FollowedShopsViewSet, basename="followed-shop")

urlpatterns = router.urls
