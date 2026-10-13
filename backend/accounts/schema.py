from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiParameter

from accounts.serializers.session import LoginUserSerializer, SessionSerializer


class AuthSchema(AutoSchema):
    def get_request_serializer(self):
        return (
            super().get_request_serializer()
            if self.view.action in ("login", "register")
            else None
        )

    def get_response_serializers(self):
        if self.view.action == "logout":
            return {204: None}
        if self.view.action == "session":
            return SessionSerializer
        if self.view.action == "register":
            return {201: LoginUserSerializer}
        return LoginUserSerializer

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
