import io

from django.db.models import F
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from categories.services.publication import visible_categories
from listings.models import ListingMetric
from listings.pagination import ListingPagination
from listings.schemas.discovery import DiscoverySchema, HomeSchema
from listings.serializers.discovery import ListingPublicSerializer, ListingSearchSerializer
from listings.services.search import public_listings, search_listings
from listings.throttles import MarketplaceReadThrottle


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


