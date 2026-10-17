from rest_framework.routers import SimpleRouter

from categories.views.public import CategoryViewSet

router = SimpleRouter(use_regex_path=False)
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = router.urls
