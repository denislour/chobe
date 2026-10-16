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
from shops.upload_handlers import ShopImageUploadHandler


@method_decorator(never_cache, name="dispatch")
class ShopViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (AccountMutationThrottle,)
    serializer_class = ShopSerializer
    serializers_by_action: ClassVar[dict] = {
    }
    schema = ShopSchema()

    def initialize_request(self, request, *args, **kwargs):
        request.upload_handlers.insert(0, ShopImageUploadHandler(request))
        return super().initialize_request(request, *args, **kwargs)

    def get_queryset(self):
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return Shop.objects.none()
        return Shop.objects.filter(owner=self.request.user, owner__is_active=True)

    def get_serializer_class(self):
        return self.serializers_by_action.get(self.action, self.serializer_class)

    def get_serializer(self, *args, **kwargs):
        error = getattr(self.request._request, "shop_upload_error", None)
        if error:
            raise ValidationError(error)
        return super().get_serializer(*args, **kwargs)

    def mine(self, request):
        shop = get_object_or_404(self.get_queryset())
        return Response(self.get_serializer(shop).data)

    def image(self, request, pk=None, kind=None):
        if kind not in {"logo", "banner"}:
            raise Http404
        content = getattr(self.get_object(), kind)
        if not content:
            raise Http404
        response = FileResponse(io.BytesIO(bytes(content)), content_type="image/jpeg")
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response
