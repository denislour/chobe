from typing import ClassVar

from common.schemas import CSRFSchema
from listings.serializers.reports import ReportAuditSerializer, ReportSerializer


class ReportSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: ReportSerializer(many=True)},
        "retrieve": {200: ReportSerializer},
        "create": {201: ReportSerializer},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]


class ReportManagementSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: ReportSerializer(many=True)},
        "retrieve": {200: ReportSerializer},
        "decision": {200: ReportSerializer},
        "history": {200: ReportAuditSerializer(many=True)},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]
