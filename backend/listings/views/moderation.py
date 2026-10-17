from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from listings.models import ModerationCase
from listings.pagination import ListingPagination
from listings.permissions import ModerationPermission
from listings.schemas.moderation import ModerationSchema
from listings.serializers.management import (
    ListingAuditSerializer,
    ModerationDecisionSerializer,
    ModerationSerializer,
)
from listings.services.moderation import decide_listing
from listings.throttles import MarketplaceMutationThrottle, MarketplaceReadThrottle


@method_decorator(never_cache, name="dispatch")
class ModerationViewSet(ModelViewSet):
    permission_classes = (ModerationPermission,)
    throttle_classes = (
        MarketplaceReadThrottle,
        MarketplaceMutationThrottle,
    )
    serializer_class = ModerationSerializer
    pagination_class = ListingPagination
    schema = ModerationSchema()
    lookup_value_converter = "int"

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(
            action in ("list", "retrieve", "decision", "history", "image")
            for action in actions
        ):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        queryset = ModerationCase.objects.select_related(
            "revision__listing__shop__owner"
        ).filter(revision__listing__deleted_at__isnull=True)
        if self.action == "list":
            queryset = queryset.filter(
                revision__version=F("revision__listing__submitted_version")
            )
            status = self.request.query_params.get("status")
            if status in ("pending", "approved", "rejected"):
                queryset = queryset.filter(status=status)
            if self.request.query_params.get("appeals") == "true":
                queryset = queryset.filter(appeal_open=True)
        return queryset

    @action(
        detail=True, methods=["post"], serializer_class=ModerationDecisionSerializer
    )
    def decision(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = decide_listing(
            request.user, self.get_object(), serializer.validated_data
        )
        return Response(ModerationSerializer(case).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        case = self.get_object()
        return Response(
            ListingAuditSerializer(
                case.revision.listing.audit_events.all()[:100], many=True
            ).data
        )

    @action(detail=True, methods=["get"], url_path="image/<uuid:image_id>")
    def image(self, request, pk=None, image_id=None):
        import io

        from django.http import FileResponse, Http404

        case = self.get_object()
        if str(image_id) not in case.revision.snapshot["images"]:
            raise Http404
        image = get_object_or_404(case.revision.listing.images, pk=image_id)
        response = FileResponse(
            io.BytesIO(bytes(image.content)), content_type="image/jpeg"
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response
