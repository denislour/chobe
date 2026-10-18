from typing import ClassVar

from drf_spectacular.types import OpenApiTypes

from accounts.serializers.profile import ProfileSerializer
from common.schemas import CSRFSchema


class ProfileSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "me": ProfileSerializer,
        "update_me": ProfileSerializer,
        "avatar": {(200, "image/jpeg"): OpenApiTypes.BINARY},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]
