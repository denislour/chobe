from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from common.pagination import ListingPagination
from common.throttles import (
    MarketplaceMutationThrottle,
    MarketplaceReadThrottle,
    ReportThrottle,
)
from listings.models import Report
from listings.schemas.reports import ReportManagementSchema, ReportSchema
from listings.serializers.reports import (
    ReportAuditSerializer,
    ReportDecisionSerializer,
    ReportSerializer,
)
from listings.services.reports import decide_report
from moderation.permissions import ReportReviewPermission


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


@method_decorator(never_cache, name="dispatch")
class ReportManagementViewSet(ModelViewSet):
    permission_classes = (ReportReviewPermission,)
    throttle_classes = (
        MarketplaceReadThrottle,
        MarketplaceMutationThrottle,
    )
    serializer_class = ReportSerializer
    schema = ReportManagementSchema()
    pagination_class = ListingPagination
    lookup_value_converter = "uuid"

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(
            action in ("list", "retrieve", "decision", "history") for action in actions
        ):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        queryset = Report.objects.all()
        if (
            self.action == "list"
            and self.request.query_params.get("status") in Report.Status.values
        ):
            queryset = queryset.filter(status=self.request.query_params["status"])
        return queryset

    @action(detail=True, methods=["post"], serializer_class=ReportDecisionSerializer)
    def decision(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = decide_report(
            request.user, self.get_object(), serializer.validated_data
        )
        return Response(ReportSerializer(report).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return Response(
            ReportAuditSerializer(
                self.get_object().decisions.all().order_by("-pk")[:100], many=True
            ).data
        )
