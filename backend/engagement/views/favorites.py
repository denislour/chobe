from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.services.privacy import viewing_history_for
from common.pagination import ListingPagination
from common.throttles import MarketplaceMutationThrottle, MarketplaceReadThrottle
from discovery.queries import public_listings
from discovery.serializers import ListingPublicSerializer
from engagement.models import Favorite
from engagement.schemas.favorites import FavoriteSchema
from listings.models import Listing


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
