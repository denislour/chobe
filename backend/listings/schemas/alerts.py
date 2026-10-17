from typing import ClassVar

from accounts.schemas.base import CSRFSchema
from listings.serializers.alerts import SavedSearchSerializer


class SavedSearchSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: SavedSearchSerializer(many=True)},
        "retrieve": {200: SavedSearchSerializer},
        "create": {201: SavedSearchSerializer},
        "partial_update": {200: SavedSearchSerializer},
        "destroy": {204: None},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]




