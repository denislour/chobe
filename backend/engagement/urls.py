from rest_framework.routers import SimpleRouter

from engagement.views.favorites import FavoriteViewSet

router = SimpleRouter(use_regex_path=False)
router.register("me/favorites", FavoriteViewSet, basename="favorite")

urlpatterns = router.urls
