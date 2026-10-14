from typing import ClassVar

from accounts.schemas.base import CSRFSchema
from accounts.serializers.privacy import ViewingHistorySerializer


class ViewingHistorySchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": ViewingHistorySerializer,
        "create": {201: ViewingHistorySerializer, 204: None},
        "clear": {204: None},
    }

    def get_request_serializer(self):
        if self.view.action != "create":
            return None
        return super().get_request_serializer()

    def get_response_serializers(self):
        return self.responses[self.view.action]
