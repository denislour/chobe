from rest_framework.routers import SimpleRouter

from engagement.views.favorites import FavoriteViewSet
from engagement.views.following import FollowedShopsViewSet
from engagement.views.searches import SavedSearchViewSet

router = SimpleRouter(use_regex_path=False)
router.register("me/favorites", FavoriteViewSet, basename="favorite")
router.register("me/saved-searches", SavedSearchViewSet, basename="saved-search")
router.register("me/followed-shops", FollowedShopsViewSet, basename="followed-shop")

urlpatterns = router.urls
