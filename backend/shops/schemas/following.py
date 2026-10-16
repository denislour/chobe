from typing import ClassVar

from accounts.schemas.base import CSRFSchema
from shops.serializers.storefront import StorefrontSerializer


class FollowingSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": StorefrontSerializer,
        "update": {204: None},
        "destroy": {204: None},
    }

    def get_request_serializer(self):
        return None

    def get_response_serializers(self):
        return self.responses[self.view.action]
