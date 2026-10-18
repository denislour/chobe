from typing import ClassVar

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse

from common.schemas import CSRFSchema
from shops.serializers.storefront import StorefrontSerializer


class StorefrontSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "retrieve": {
            200: StorefrontSerializer,
            308: OpenApiResponse(description="Use the canonical URL in Location."),
        },
        "image": {(200, "image/jpeg"): OpenApiTypes.BINARY},
    }

    def get_request_serializer(self):
        return None

    def get_response_serializers(self):
        return self.responses[self.view.action]

    def get_override_parameters(self):
        return [
            OpenApiParameter(
                "slug", location=OpenApiParameter.PATH, required=True, type=str
            )
        ]
