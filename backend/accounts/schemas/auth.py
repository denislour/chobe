from typing import ClassVar

from accounts.schemas.base import CSRFSchema
from accounts.serializers.session import AuthUserSerializer, SessionSerializer


class AuthSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "login": AuthUserSerializer,
        "register": {201: AuthUserSerializer},
        "session": SessionSerializer,
        "logout": {204: None},
    }

    def get_request_serializer(self):
        if self.view.action not in ("login", "register"):
            return None
        return super().get_request_serializer()

    def get_response_serializers(self):
        return self.responses[self.view.action]
