import json

from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.exceptions import Throttled
from accounts.models import AccountDataExport
from accounts.services.account_data import downloadable_account_data, request_account_data_export

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.schemas.base import CSRFSchema
from accounts.schemas.privacy import AccountDataExportSchema, ViewingHistorySchema
from accounts.serializers.privacy import AccountDataExportSerializer, PrivacySerializer, ViewingHistorySerializer
from accounts.services.privacy import clear_viewing_history, privacy_for, record_viewing_history, viewing_history_for
from accounts.throttles import AccountDataExportThrottle, AccountMutationThrottle, HistoryThrottle


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


@method_decorator(never_cache, name="dispatch")
class AccountDataExportViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = AccountDataExportSerializer
    schema = AccountDataExportSchema()
    http_method_names = ("get", "post", "head", "options")
    throttle_classes = (AccountDataExportThrottle,)

    def throttled(self, request, wait):
        raise Throttled(
            wait, detail="You have reached the limit of 2 account exports per hour."
        )

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return AccountDataExport.objects.none()
        return AccountDataExport.objects.filter(user=self.request.user)

    def list(self, request):
        return Response(self.get_serializer(self.get_queryset()[:10], many=True).data)

    def create(self, request):
        job = request_account_data_export(request.user)
        return Response(self.get_serializer(job).data, status=202)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        job = self.get_object()
        payload = downloadable_account_data(job)
        response = HttpResponse(json.dumps(payload), content_type="application/json")
        response["Content-Disposition"] = (
            f'attachment; filename="chobe-account-data-{job.pk}.json"'
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
