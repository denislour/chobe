from typing import ClassVar

from drf_spectacular.types import OpenApiTypes

from common.schemas import CSRFSchema
from discovery.serializers import (
    HomePayloadSerializer,
    ListingPublicSerializer,
)


class DiscoverySchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: ListingPublicSerializer(many=True)},
        "retrieve": {200: ListingPublicSerializer},
        "image": {200: OpenApiTypes.BINARY},
        "events": {204: None},
        "compare": {200: OpenApiTypes.OBJECT},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]


class HomeSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: HomePayloadSerializer(many=False)},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]
