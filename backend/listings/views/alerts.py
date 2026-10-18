from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from common.pagination import ListingPagination
from listings.models import Notification, NotificationPreference, SavedSearch
from listings.schemas.alerts import (
    NotificationSchema,
    PreferenceSchema,
    SavedSearchSchema,
)
from listings.serializers.alerts import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
    SavedSearchSerializer,
)
from listings.services.search import public_listings
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


@method_decorator(never_cache, name="dispatch")
class NotificationViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (
        MarketplaceReadThrottle,
        MarketplaceMutationThrottle,
    )
    serializer_class = NotificationSerializer
    pagination_class = ListingPagination
    schema = NotificationSchema()
    lookup_value_converter = "int"

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(action in ("list", "read", "read_all") for action in actions):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_queryset(self):
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user).select_related(
            "listing", "search"
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context["visible_ids"] = set(
                public_listings()
                .filter(notification__user=self.request.user)
                .values_list("pk", flat=True)
            )
        return context

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=("read_at",))
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response(status=204)


@method_decorator(never_cache, name="dispatch")
class NotificationPreferenceViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (
        MarketplaceReadThrottle,
        MarketplaceMutationThrottle,
    )
    serializer_class = NotificationPreferenceSerializer
    schema = PreferenceSchema()

    def get_permissions(self):
        actions = (
            self.action_map.values() if self.action == "metadata" else (self.action,)
        )
        if not any(action in ("me", "update_me") for action in actions):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def get_object(self):
        return NotificationPreference.objects.get_or_create(user=self.request.user)[0]

    @action(detail=False, methods=["get"])
    def me(self, request):
        return self.retrieve(request)

    @me.mapping.patch
    def update_me(self, request):
        return self.partial_update(request)
