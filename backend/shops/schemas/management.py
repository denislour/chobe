from typing import ClassVar

from drf_spectacular.types import OpenApiTypes

from common.schemas import CSRFSchema
from shops.serializers.management import ShopPreviewSerializer, ShopSerializer


class ShopSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "mine": ShopSerializer,
        "create": {201: ShopSerializer},
        "partial_update": ShopSerializer,
        "status": ShopSerializer,
        "preview": ShopPreviewSerializer,
        "image": {(200, "image/jpeg"): OpenApiTypes.BINARY},
    }

    def get_request_serializer(self):
        if self.view.action in {"mine", "preview", "image"}:
            return None
        return super().get_request_serializer()

    def get_response_serializers(self):
        return self.responses[self.view.action]
