from typing import ClassVar

from accounts.schemas.base import CSRFSchema
from categories.serializers.management import (
    CategoryAuditSerializer,
    CategoryDraftSerializer,
    CategoryRevisionSerializer,
    TaxonomyCapabilitiesSerializer,
)


class CategoryManagementSchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": CategoryDraftSerializer,
        "retrieve": CategoryDraftSerializer,
        "create": {201: CategoryDraftSerializer},
        "partial_update": CategoryDraftSerializer,
        "publish": CategoryDraftSerializer,
        "retire": CategoryDraftSerializer,
        "revisions": CategoryRevisionSerializer(many=True),
        "history": CategoryAuditSerializer(many=True),
        "capabilities": TaxonomyCapabilitiesSerializer,
    }

    def get_request_serializer(self):
        if self.view.action in (
            "list",
            "retrieve",
            "revisions",
            "history",
            "capabilities",
        ):
            return None
        return super().get_request_serializer()

    def get_response_serializers(self):
        return self.responses[self.view.action]
