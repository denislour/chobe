from typing import ClassVar

from accounts.schemas.base import CSRFSchema
from categories.serializers.public import (
    CategoryFacetsSerializer,
    CategorySerializer,
    ValidatedCategoryValuesSerializer,
)


class CategorySchema(CSRFSchema):
    responses: ClassVar[dict] = {
        "list": CategorySerializer,
        "retrieve": CategorySerializer,
        "facets": CategoryFacetsSerializer,
        "validate_attributes": ValidatedCategoryValuesSerializer,
    }

    def get_override_parameters(self):
        return []

    def get_request_serializer(self):
        if self.view.action != "validate_attributes":
            return None
        return super().get_request_serializer()

    def get_response_serializers(self):
        return self.responses[self.view.action]
