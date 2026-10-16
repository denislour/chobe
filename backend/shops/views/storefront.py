import io

from django.db.models import Exists, OuterRef
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from shops.models import Shop, ShopFollow
from shops.schemas.storefront import StorefrontSchema
from shops.serializers.storefront import StorefrontSerializer
from shops.throttles import StorefrontReadThrottle


@method_decorator(never_cache, name="dispatch")
class StorefrontViewSet(ModelViewSet):
    permission_classes = (AllowAny,)
    throttle_classes = (StorefrontReadThrottle,)
    serializer_class = StorefrontSerializer
    lookup_field = "slug"
    lookup_value_converter = "slug"
    schema = StorefrontSchema()

    def get_permissions(self):
        actions = self.action_map.values() if self.action == "metadata" else (self.action,)
        if not any(action in ("retrieve", "image") for action in actions):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        shops = Shop.objects.filter(status=Shop.Status.ACTIVE, owner__is_active=True)
        if getattr(self, "swagger_fake_view", False):
            return shops.none()
        user = self.request.user
        if user.is_authenticated:
            shops = shops.annotate(
                is_following=Exists(
                    ShopFollow.objects.filter(user=user, shop_id=OuterRef("pk"))
                )
            )
        return shops

    def get_object(self):
        shop = get_object_or_404(self.get_queryset(), slugs__slug=self.kwargs["slug"])
        self.check_object_permissions(self.request, shop)
        return shop

    def retrieve(self, request, slug=None):
        shop = self.get_object()
        if self.kwargs["slug"] != shop.slug:
            return HttpResponse(
                status=308,
                headers={
                    "Location": reverse("storefront-detail", kwargs={"slug": shop.slug})
                },
            )
        return Response(self.get_serializer(shop).data)

    @action(
        detail=True,
        methods=["get"],
        url_path="images/<str:kind>",
        url_name="image",
    )
    def image(self, request, slug=None, kind=None):
        if kind not in {"logo", "banner"}:
            raise Http404
        content = getattr(self.get_object(), kind)
        if not content:
            raise Http404
        response = FileResponse(io.BytesIO(bytes(content)), content_type="image/jpeg")
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response
