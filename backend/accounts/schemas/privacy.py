from typing import ClassVar

from drf_spectacular.types import OpenApiTypes

from accounts.schemas.base import CSRFSchema
from accounts.serializers.privacy import (
    AccountDataExportSerializer,
    DeletionReceiptSerializer,
    DeletionStatusSerializer,
    PrivacySerializer,
    ViewingHistorySerializer,
)


class AccountDataExportSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": AccountDataExportSerializer,
        "retrieve": AccountDataExportSerializer,
        "create": {202: AccountDataExportSerializer},
        "download": OpenApiTypes.BINARY,
    }

    def get_request_serializer(self):
        return None

    def get_response_serializers(self):
        return self.responses[self.view.action]


class DeletionSchema(CSRFSchema):
    responses: ClassVar[dict] = {"create": {202: DeletionReceiptSerializer}}

    def get_response_serializers(self):
        return self.responses[self.view.action]


class DeletionStatusSchema(CSRFSchema):
    responses: ClassVar[dict] = {"retrieve": DeletionStatusSerializer}

    def get_response_serializers(self):
        return self.responses[self.view.action]


class PrivacySchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "me": PrivacySerializer,
        "update_me": PrivacySerializer,
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]


class ViewingHistorySchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": ViewingHistorySerializer,
        "create": {201: ViewingHistorySerializer, 204: None},
        "clear": {204: None},
    }

    def get_request_serializer(self):
        if self.view.action != "create":
            return None
        return super().get_request_serializer()

    def get_response_serializers(self):
        return self.responses[self.view.action]
