from typing import ClassVar

from common.schemas import CSRFSchema
from listings.serializers.alerts import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
    SavedSearchSerializer,
)


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


class NotificationSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": {200: NotificationSerializer(many=True)},
        "read": {200: NotificationSerializer},
        "read_all": {204: None},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]


class PreferenceSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "me": {200: NotificationPreferenceSerializer},
        "update_me": {200: NotificationPreferenceSerializer},
    }

    def get_response_serializers(self):
        return self.responses[self.view.action]
