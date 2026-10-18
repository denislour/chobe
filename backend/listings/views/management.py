import csv
import io

from django.db.models import Count
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from common.pagination import ListingPagination
from common.throttles import MarketplaceMutationThrottle, MarketplaceReadThrottle
from listings.models import Listing
from listings.schemas.management import ListingManagementSchema
from listings.serializers.management import (
    AppealSerializer,
    ImageOrderSerializer,
    ImageUploadSerializer,
    ListingAuditSerializer,
    ListingDraftSerializer,
    ListingStatusSerializer,
    ListingVersionSerializer,
)
from listings.services.images import add_image, arrange_images
from listings.services.management import (
    change_status,
    delete_listing,
    draft_snapshot,
    renew_listing,
)
from moderation.serializers.reviews import (
    ModerationSerializer,
)
from workflows.listing_moderation import appeal_listing
from workflows.listing_submission import submit_for_review


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
                "destroy",
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

    def destroy(self, request, pk=None):
        serializer = ListingVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        delete_listing(
            request.user, self.get_object(), serializer.validated_data["version"]
        )
        return Response(status=204)

    @action(detail=True, methods=["post"], serializer_class=ListingVersionSerializer)
    def submit(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = submit_for_review(
            request.user, self.get_object(), serializer.validated_data["version"]
        )
        return Response(ListingDraftSerializer(listing).data)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        return Response(draft_snapshot(self.get_object()))

    @action(detail=True, methods=["post"], serializer_class=ListingStatusSerializer)
    def status(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = change_status(
            request.user,
            self.get_object(),
            serializer.validated_data["version"],
            serializer.validated_data["status"],
        )
        return Response(ListingDraftSerializer(listing).data)

    @action(detail=True, methods=["post"], serializer_class=ListingVersionSerializer)
    def renew(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = renew_listing(
            request.user, self.get_object(), serializer.validated_data["version"]
        )
        return Response(ListingDraftSerializer(listing).data)

    @action(detail=True, methods=["get"])
    def retention(self, request, pk=None):
        listing = self.get_object()
        return Response(
            {
                "last_owner_action_at": listing.last_owner_action_at,
                "retention_due_at": listing.retention_due_at,
                "policy": "Deleted after six calendar months without an eligible owner action.",
            }
        )

    @action(detail=True, methods=["post"], serializer_class=ImageUploadSerializer)
    def images(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = add_image(
            request.user,
            self.get_object(),
            serializer.validated_data["version"],
            serializer.validated_data["image"],
        )
        return Response(ListingDraftSerializer(listing).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="images/order",
        serializer_class=ImageOrderSerializer,
    )
    def order_images(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = arrange_images(
            request.user,
            self.get_object(),
            serializer.validated_data["version"],
            [str(pk) for pk in serializer.validated_data["images"]],
        )
        return Response(ListingDraftSerializer(listing).data)

    @action(detail=True, methods=["get"], url_path="image/<uuid:image_id>")
    def image(self, request, pk=None, image_id=None):
        image = get_object_or_404(self.get_object().images, pk=image_id)
        response = FileResponse(
            io.BytesIO(bytes(image.content)), content_type="image/jpeg"
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response

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

    @action(detail=True, methods=["post"], serializer_class=AppealSerializer)
    def appeal(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = appeal_listing(
            request.user, self.get_object(), **serializer.validated_data
        )
        return Response(ListingDraftSerializer(listing).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return Response(
            ListingAuditSerializer(
                self.get_object().audit_events.all()[:100], many=True
            ).data
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        counts = self.get_queryset().values("status").annotate(count=Count("pk"))
        return Response({row["status"]: row["count"] for row in counts})

    @action(detail=False, methods=["get"])
    def export(self, request):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="chobe-listings.csv"'
        writer = csv.writer(response)
        writer.writerow(
            (
                "ID",
                "Title",
                "Status",
                "Price mode",
                "Price VND",
                "Area",
                "Retention due",
            )
        )
        for listing in self.get_queryset()[:1000]:
            row = (
                listing.pk,
                listing.title,
                listing.status,
                listing.price_mode,
                listing.price,
                listing.area,
                listing.retention_due_at.isoformat(),
            )
            writer.writerow(
                [
                    "'" + value
                    if isinstance(value, str)
                    and value.lstrip().startswith(("=", "+", "-", "@"))
                    else value
                    for value in row
                ]
            )
        return response
