from typing import ClassVar

from drf_spectacular.types import OpenApiTypes

from common.schemas import CSRFSchema
from listings.serializers.management import ListingAuditSerializer
from moderation.serializers.reviews import ModerationSerializer


class ModerationSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: ModerationSerializer(many=True)},
        "retrieve": {200: ModerationSerializer},
        "decision": {200: ModerationSerializer},
        "history": {200: ListingAuditSerializer(many=True)},
        "image": {200: OpenApiTypes.BINARY},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]
