from typing import ClassVar

from drf_spectacular.types import OpenApiTypes

from accounts.schemas.base import CSRFSchema
from accounts.serializers.profile import ProfileSerializer


class ProfileSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "retrieve": ProfileSerializer,
        "partial_update": ProfileSerializer,
        "avatar": {(200, "image/jpeg"): OpenApiTypes.BINARY},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]
