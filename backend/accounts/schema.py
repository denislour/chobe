from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiParameter

from .serializers import LoginUserSerializer


class LoginSchema(AutoSchema):
    def get_response_serializers(self):
        if self.view.action == "csrf":
            return {204: None}
        return LoginUserSerializer

    def get_override_parameters(self):
        if self.view.action != "login":
            return []
        return [
            OpenApiParameter(
                "X-XSRF-TOKEN",
                location=OpenApiParameter.HEADER,
                required=True,
                description="CSRF token from the XSRF-TOKEN cookie.",
            )
        ]
