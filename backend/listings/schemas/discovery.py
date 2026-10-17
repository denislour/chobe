from typing import ClassVar

from drf_spectacular.types import OpenApiTypes

from accounts.schemas.base import CSRFSchema
from listings.serializers.discovery import ListingPublicSerializer


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
        "list": {200: OpenApiTypes.OBJECT},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]


class FavoriteSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: ListingPublicSerializer(many=True)},
        "update": {204: None},
        "destroy": {204: None},
        "history": {200: ListingPublicSerializer(many=True)},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]
