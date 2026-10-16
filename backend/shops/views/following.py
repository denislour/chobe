from django.db.models import Value
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.throttles import AccountMutationThrottle
from shops.models import Shop, ShopFollow
from shops.schemas.following import FollowingSchema
from shops.serializers.storefront import StorefrontSerializer
from shops.services.following import follow_shop


class FollowedShopsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


@method_decorator(never_cache, name="dispatch")
class FollowedShopsViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (AccountMutationThrottle,)
    serializer_class = StorefrontSerializer
    pagination_class = FollowedShopsPagination
    lookup_url_kwarg = "shop_id"
    lookup_value_converter = "uuid"
    schema = FollowingSchema()

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(action in ("list", "update", "destroy") for action in actions):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Shop.objects.none()
        return (
            Shop.objects.filter(
                followers__user=self.request.user,
                status=Shop.Status.ACTIVE,
                owner__is_active=True,
            )
            .annotate(is_following=Value(True))
            .order_by("-followers__created_at", "-followers__pk")
        )

    def update(self, request, shop_id=None):
        follow_shop(request.user, shop_id)
        return Response(status=204)

    def destroy(self, request, shop_id=None):
        ShopFollow.objects.filter(user=request.user, shop_id=shop_id).delete()
        return Response(status=204)
