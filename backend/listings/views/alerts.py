from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from listings.models import SavedSearch
from listings.pagination import ListingPagination
from listings.schemas.alerts import SavedSearchSchema
from listings.serializers.alerts import SavedSearchSerializer
from listings.throttles import MarketplaceMutationThrottle, MarketplaceReadThrottle


@method_decorator(never_cache, name="dispatch")
class SavedSearchViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (
        MarketplaceReadThrottle,
        MarketplaceMutationThrottle,
    )
    serializer_class = SavedSearchSerializer
    pagination_class = ListingPagination
    schema = SavedSearchSchema()
    lookup_value_converter = "int"

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(
            action in ("list", "retrieve", "create", "partial_update", "destroy")
            for action in actions
        ):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return SavedSearch.objects.none()
        return SavedSearch.objects.filter(user=self.request.user)




