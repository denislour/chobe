from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.schemas.base import CSRFSchema
from accounts.schemas.privacy import ViewingHistorySchema
from accounts.serializers.privacy import PrivacySerializer, ViewingHistorySerializer
from accounts.services.privacy import clear_viewing_history, privacy_for, record_viewing_history, viewing_history_for
from accounts.throttles import AccountMutationThrottle, HistoryThrottle


@method_decorator(never_cache, name="dispatch")
class PrivacyViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (AccountMutationThrottle,)
    serializer_class = PrivacySerializer
    schema = CSRFSchema()

    def get_object(self):
        return privacy_for(self.request.user)


@method_decorator(never_cache, name="dispatch")
class ViewingHistoryViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = ViewingHistorySerializer
    schema = ViewingHistorySchema()
    throttle_classes = (HistoryThrottle,)

    def get_queryset(self):
        return viewing_history_for(self.request.user)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = record_viewing_history(
            request.user, serializer.validated_data["listing_id"]
        )
        if entry is None:
            return Response(status=204)
        return Response(self.get_serializer(entry).data, status=201)

    def clear(self, request):
        clear_viewing_history(request.user)
        return Response(status=204)
