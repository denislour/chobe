
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from listings.models import Listing
from listings.pagination import ListingPagination
from listings.schemas.management import ListingManagementSchema
from listings.serializers.management import ListingAuditSerializer, ListingDraftSerializer, ModerationSerializer
from listings.throttles import MarketplaceMutationThrottle, MarketplaceReadThrottle


@method_decorator(never_cache, name="dispatch")
class ListingManagementViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (
        MarketplaceReadThrottle,
        MarketplaceMutationThrottle,
    )
    serializer_class = ListingDraftSerializer
    schema = ListingManagementSchema()
    pagination_class = ListingPagination
    lookup_value_converter = "int"

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(
            action
            in (
                "list",
                "retrieve",
                "create",
                "partial_update",
                "submit",
                "preview",
                "status",
                "renew",
                "retention",
                "images",
                "order_images",
                "image",
                "moderation",
                "appeal",
                "history",
                "summary",
                "export",
            )
            for action in actions
        ):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return Listing.objects.none()
        queryset = (
            Listing.objects.filter(shop__owner=self.request.user)
            .exclude(status="deleted")
            .select_related("shop")
        )
        if self.action == "list":
            state = self.request.query_params.get("state")
            if state:
                if state not in Listing.Status.values:
                    raise ValidationError(
                        {"state": ["Choose a supported listing status."]}
                    )
                queryset = queryset.filter(status=state)
            query = self.request.query_params.get("q", "")
            if len(query) > 160:
                raise ValidationError({"q": ["Use up to 160 characters."]})
            if query:
                queryset = queryset.filter(title__icontains=query)
            if self.request.query_params.get("retention") == "due":
                from datetime import timedelta

                queryset = queryset.filter(
                    retention_due_at__lte=timezone.now() + timedelta(days=14)
                )
        return queryset










    @action(detail=True, methods=["get"])
    def moderation(self, request, pk=None):
        cases = (
            self.get_object()
            .revisions.filter(moderation__isnull=False)
            .select_related("moderation", "moderation__revision__listing")[:30]
        )
        return Response(
            ModerationSerializer(
                [revision.moderation for revision in cases], many=True
            ).data
        )


    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return Response(
            ListingAuditSerializer(
                self.get_object().audit_events.all()[:100], many=True
            ).data
        )


