from rest_framework.routers import SimpleRouter

from categories.views.management import CategoryManagementViewSet
from categories.views.public import CategoryViewSet

router = SimpleRouter(use_regex_path=False)
router.register("categories", CategoryViewSet, basename="category")
router.register(
    "admin/categories", CategoryManagementViewSet, basename="category-management"
)

urlpatterns = router.urls
