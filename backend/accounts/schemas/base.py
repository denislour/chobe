from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiParameter


class CSRFSchema(AutoSchema):
    def get_override_parameters(self):
        if self.method in ("GET", "HEAD", "OPTIONS"):
            return []
        return [
            OpenApiParameter(
                "X-XSRF-TOKEN",
                location=OpenApiParameter.HEADER,
                required=True,
                description="CSRF token from the XSRF-TOKEN cookie.",
            )
        ]
