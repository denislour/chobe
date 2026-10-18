import io

from django.db.models import F
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.services.privacy import viewing_history_for
from categories.services.publication import visible_categories
from common.pagination import ListingPagination
from common.throttles import (
    ContactThrottle,
    MarketplaceMutationThrottle,
    MarketplaceReadThrottle,
)
from listings.models import Favorite, Listing, ListingMetric
from listings.schemas.discovery import DiscoverySchema, FavoriteSchema, HomeSchema
from listings.serializers.discovery import (
    CompareQuerySerializer,
    ContactEventSerializer,
    ListingPublicSerializer,
    ListingSearchSerializer,
)
from listings.services.search import public_listings, search_listings


@method_decorator(never_cache, name="dispatch")
class ListingViewSet(ModelViewSet):
    permission_classes = (AllowAny,)
    throttle_classes = (MarketplaceReadThrottle,)
    serializer_class = ListingPublicSerializer
    schema = DiscoverySchema()
    pagination_class = ListingPagination
    lookup_value_converter = "int"

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(
            action in ("list", "retrieve", "image", "events", "compare")
            for action in actions
        ):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        if self.action == "list":
            serializer = ListingSearchSerializer(data=self.request.query_params)
            serializer.is_valid(raise_exception=True)
            return search_listings(serializer.validated_data)
        return public_listings()

    def retrieve(self, request, pk=None):
        listing = self.get_object()
        metric, _ = ListingMetric.objects.get_or_create(
            listing=listing, day=timezone.localdate(), kind="view"
        )
        ListingMetric.objects.filter(pk=metric.pk).update(count=F("count") + 1)
        return Response(self.get_serializer(listing).data)

    @action(detail=True, methods=["get"], url_path="image/<uuid:image_id>")
    def image(self, request, pk=None, image_id=None):
        listing = self.get_object()
        if str(image_id) not in listing.published["images"]:
            raise Http404
        image = get_object_or_404(listing.images, pk=image_id)
        response = FileResponse(
            io.BytesIO(bytes(image.content)), content_type="image/jpeg"
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response

    @action(
        detail=True,
        methods=["post"],
        serializer_class=ContactEventSerializer,
        throttle_classes=[ContactThrottle],
    )
    def events(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = self.get_object()
        if not ListingPublicSerializer(listing).data["phone"]:
            raise ValidationError("This seller has not shared a phone number.")
        metric, _ = ListingMetric.objects.get_or_create(
            listing=listing,
            day=timezone.localdate(),
            kind=serializer.validated_data["kind"],
        )
        ListingMetric.objects.filter(pk=metric.pk).update(count=F("count") + 1)
        return Response(status=204)

    @action(detail=False, methods=["get"])
    def compare(self, request):
        serializer = CompareQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]
        by_id = {
            listing.pk: listing for listing in public_listings().filter(pk__in=ids)
        }
        listings = [by_id[pk] for pk in ids if pk in by_id]
        categories = {listing.published["category"] for listing in listings}
        if len(categories) > 1:
            raise ValidationError("Compare listings from the same category.")
        return Response(
            {
                "results": ListingPublicSerializer(
                    listings, many=True, context=self.get_serializer_context()
                ).data,
                "unavailable": [pk for pk in ids if pk not in by_id],
            }
        )


@method_decorator(never_cache, name="dispatch")
class HomeViewSet(ModelViewSet):
    permission_classes = (AllowAny,)
    throttle_classes = (MarketplaceReadThrottle,)
    serializer_class = ListingPublicSerializer
    schema = HomeSchema()

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(action == "list" for action in actions):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def list(self, request):
        return Response(
            {
                "categories": list(visible_categories().values()),
                "latest": ListingPublicSerializer(
                    public_listings().order_by("-published_at", "-pk")[:20],
                    many=True,
                    context=self.get_serializer_context(),
                ).data,
            }
        )


@method_decorator(never_cache, name="dispatch")
class FavoriteViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (
        MarketplaceReadThrottle,
        MarketplaceMutationThrottle,
    )
    serializer_class = ListingPublicSerializer
    schema = FavoriteSchema()
    pagination_class = ListingPagination
    lookup_value_converter = "int"

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(
            action in ("list", "update", "destroy", "history") for action in actions
        ):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return Listing.objects.none()
        return (
            public_listings()
            .filter(favorites__user=self.request.user)
            .order_by("-favorites__created_at", "-pk")
        )

    def update(self, request, pk=None):
        listing = get_object_or_404(public_listings(), pk=pk)
        Favorite.objects.get_or_create(user=request.user, listing=listing)
        return Response(status=204)

    def destroy(self, request, pk=None):
        Favorite.objects.filter(user=request.user, listing_id=pk).delete()
        return Response(status=204)

    @action(detail=False, methods=["get"])
    def history(self, request):
        ids = list(
            viewing_history_for(request.user).values_list("listing_id", flat=True)
        )
        by_id = {
            listing.pk: listing for listing in public_listings().filter(pk__in=ids)
        }
        return Response(
            ListingPublicSerializer(
                [by_id[pk] for pk in ids if pk in by_id],
                many=True,
                context=self.get_serializer_context(),
            ).data
        )
