from typing import ClassVar

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from common.schemas import CSRFSchema
from discovery.serializers import (
    CompareQuerySerializer,
    HomePayloadSerializer,
    ListingPublicSerializer,
    ListingSearchSerializer,
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

    def get_override_parameters(self):
        parameters = super().get_override_parameters()
        if self.view.action == "list":
            return [
                *parameters,
                ListingSearchSerializer,
                OpenApiParameter(
                    "attributes",
                    type=OpenApiTypes.STR,
                    description="JSON object containing typed category attribute filters.",
                ),
            ]
        if self.view.action == "compare":
            return [*parameters, CompareQuerySerializer]
        return parameters


class HomeSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: HomePayloadSerializer(many=False)},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]
