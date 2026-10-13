from typing import ClassVar

from accounts.schemas.base import CSRFSchema


class PasswordResetSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "forgot_password": {202: None},
        "reset_password": {204: None},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]
