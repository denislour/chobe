from rest_framework.routers import SimpleRouter

from moderation.views.reviews import ModerationViewSet

router = SimpleRouter(use_regex_path=False)
router.register("admin/moderation", ModerationViewSet, basename="moderation")

urlpatterns = router.urls
