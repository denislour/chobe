from typing import ClassVar

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiParameter

from accounts.serializers.session import AuthUserSerializer, SessionSerializer


class AuthSchema(AutoSchema):
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

    def get_override_parameters(self):
        if self.view.action not in ("login", "logout", "register"):
            return []
        return [
            OpenApiParameter(
                "X-XSRF-TOKEN",
                location=OpenApiParameter.HEADER,
                required=True,
                description="CSRF token from the XSRF-TOKEN cookie.",
            )
        ]
