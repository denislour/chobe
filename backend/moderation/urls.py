from rest_framework.routers import SimpleRouter

from moderation.views.reports import ReportManagementViewSet, ReportViewSet
from moderation.views.reviews import ModerationViewSet

router = SimpleRouter(use_regex_path=False)
router.register("me/reports", ReportViewSet, basename="report")
router.register("admin/moderation", ModerationViewSet, basename="moderation")
router.register("admin/reports", ReportManagementViewSet, basename="report-management")

urlpatterns = router.urls
