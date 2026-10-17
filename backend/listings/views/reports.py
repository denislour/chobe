from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from listings.models import Report
from listings.pagination import ListingPagination
from listings.schemas.reports import ReportSchema
from listings.serializers.reports import ReportSerializer
from listings.throttles import MarketplaceReadThrottle, ReportThrottle


@method_decorator(never_cache, name="dispatch")
class ReportViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (
        MarketplaceReadThrottle,
        ReportThrottle,
    )
    serializer_class = ReportSerializer
    schema = ReportSchema()
    pagination_class = ListingPagination
    lookup_value_converter = "uuid"

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(action in ("list", "retrieve", "create") for action in actions):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return Report.objects.none()
        return Report.objects.filter(reporter=self.request.user)


