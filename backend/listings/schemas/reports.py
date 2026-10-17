from typing import ClassVar

from accounts.schemas.base import CSRFSchema
from listings.serializers.reports import ReportSerializer


class ReportSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: ReportSerializer(many=True)},
        "retrieve": {200: ReportSerializer},
        "create": {201: ReportSerializer},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]


