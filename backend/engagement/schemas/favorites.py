from typing import ClassVar

from common.schemas import CSRFSchema
from discovery.serializers import ListingPublicSerializer


class FavoriteSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: ListingPublicSerializer(many=True)},
        "update": {204: None},
        "destroy": {204: None},
        "history": {200: ListingPublicSerializer(many=True)},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]
