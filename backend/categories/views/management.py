from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.throttles import AccountMutationThrottle
from categories.models import Category
from categories.permissions import TaxonomyPermission
from categories.schemas.management import CategoryManagementSchema
from categories.serializers.management import (
    CategoryAuditSerializer,
    CategoryDraftSerializer,
    CategoryRevisionSerializer,
    CategoryVersionSerializer,
)
from categories.services.publication import publish_category, retire_category


@method_decorator(never_cache, name="dispatch")
class CategoryManagementViewSet(ModelViewSet):
    permission_classes = (TaxonomyPermission,)
    throttle_classes = (AccountMutationThrottle,)
    serializer_class = CategoryDraftSerializer
    schema = CategoryManagementSchema()
    lookup_value_converter = "uuid"
    pagination_class = None

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
                "publish",
                "retire",
                "revisions",
                "history",
                "capabilities",
            )
            for action in actions
        ):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        return Category.objects.all()

    @action(detail=True, methods=["post"], serializer_class=CategoryVersionSerializer)
    def publish(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = publish_category(
            request.user, self.get_object(), serializer.validated_data["version"]
        )
        return Response(CategoryDraftSerializer(category).data)

    @action(detail=True, methods=["post"], serializer_class=CategoryVersionSerializer)
    def retire(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = retire_category(
            request.user, self.get_object(), serializer.validated_data["version"]
        )
        return Response(CategoryDraftSerializer(category).data)

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        return Response(
            CategoryRevisionSerializer(
                self.get_object().revisions.all()[:50], many=True
            ).data
        )

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return Response(
            CategoryAuditSerializer(
                self.get_object().audit_events.all()[:50], many=True
            ).data
        )

    @action(detail=False, methods=["get"])
    def capabilities(self, request):
        user = request.user
        return Response(
            {
                "create": user.has_perm("categories.add_category"),
                "edit": user.has_perm("categories.change_category"),
                "publish": user.has_perm("categories.publish_category"),
                "retire": user.has_perm("categories.retire_category"),
            }
        )
