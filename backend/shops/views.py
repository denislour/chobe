import io
from typing import ClassVar

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.throttles import AccountMutationThrottle
from shops.models import Shop, ShopSlug
from shops.schemas import ShopSchema
from shops.serializers import (
    ShopPreviewSerializer,
    ShopSerializer,
)


@method_decorator(never_cache, name="dispatch")
class ShopViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (AccountMutationThrottle,)
    serializer_class = ShopSerializer
    serializers_by_action: ClassVar[dict] = {
    }
    schema = ShopSchema()

    def get_queryset(self):
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return Shop.objects.none()
        return Shop.objects.filter(owner=self.request.user, owner__is_active=True)

    def get_serializer_class(self):
        return self.serializers_by_action.get(self.action, self.serializer_class)

    def mine(self, request):
        shop = get_object_or_404(self.get_queryset())
        return Response(self.get_serializer(shop).data)
