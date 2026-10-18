from typing import ClassVar

from drf_spectacular.types import OpenApiTypes

from common.schemas import CSRFSchema
from listings.serializers.management import (
    ListingAuditSerializer,
    ListingDraftSerializer,
    ModerationSerializer,
)


class ListingManagementSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: ListingDraftSerializer(many=True)},
        "retrieve": {200: ListingDraftSerializer},
        "create": {201: ListingDraftSerializer},
        "partial_update": {200: ListingDraftSerializer},
        "destroy": {204: None},
        "submit": {200: ListingDraftSerializer},
        "preview": {200: OpenApiTypes.OBJECT},
        "status": {200: ListingDraftSerializer},
        "renew": {200: ListingDraftSerializer},
        "retention": {200: OpenApiTypes.OBJECT},
        "images": {200: ListingDraftSerializer},
        "order_images": {200: ListingDraftSerializer},
        "image": {200: OpenApiTypes.BINARY},
        "moderation": {200: ModerationSerializer(many=True)},
        "appeal": {200: ListingDraftSerializer},
        "history": {200: ListingAuditSerializer(many=True)},
        "summary": {200: OpenApiTypes.OBJECT},
        "export": {200: OpenApiTypes.BINARY},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]
