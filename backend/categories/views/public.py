from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from categories.models import Category
from categories.schemas.public import CategorySchema
from categories.serializers.public import CategorySerializer, CategoryValuesSerializer
from categories.services.attributes import validate_category_attributes
from categories.services.publication import visible_categories
from categories.throttles import CategoryReadThrottle


@method_decorator(never_cache, name="dispatch")
class CategoryViewSet(ModelViewSet):
    permission_classes = (AllowAny,)
    throttle_classes = (CategoryReadThrottle,)
    serializer_class = CategorySerializer
    schema = CategorySchema()
    lookup_value_converter = "uuid"
    pagination_class = None

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(
            action in ("list", "retrieve", "facets", "validate_attributes")
            for action in actions
        ):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Category.objects.none()
        return Category.objects.filter(
            status=Category.Status.ACTIVE, pk__in=visible_categories()
        )

    def list(self, request):
        categories = sorted(
            self.get_queryset(),
            key=lambda item: (
                item.published["sort_order"],
                item.published["name"],
                str(item.pk),
            ),
        )
        return Response(self.get_serializer(categories, many=True).data)

    @action(detail=True, methods=["get"])
    def facets(self, request, pk=None):
        snapshot = self.get_object().published
        return Response(
            {
                "category_id": snapshot["id"],
                "version": snapshot["version"],
                "fields": [
                    field for field in snapshot["attributes"] if field["filterable"]
                ],
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="validate-attributes",
        serializer_class=CategoryValuesSerializer,
    )
    def validate_attributes(self, request, pk=None):
        self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version = serializer.validated_data["version"]
        cleaned = validate_category_attributes(
            pk, version, serializer.validated_data["attributes"]
        )
        return Response(
            {"category_id": str(pk), "version": version, "attributes": cleaned}
        )
