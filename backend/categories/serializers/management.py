from typing import ClassVar

from rest_framework import serializers

from categories.models import Category, CategoryAuditEvent, CategoryRevision
from categories.serializers.attributes import AttributeDefinitionSerializer
from categories.services.publication import save_draft


class CategoryDraftSerializer(serializers.ModelSerializer):
    slug = serializers.RegexField(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    attributes = AttributeDefinitionSerializer(many=True, max_length=30, required=False)

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "parent",
            "sort_order",
            "restricted",
            "attributes",
            "version",
            "status",
            "published",
            "updated_at",
        )
        read_only_fields = ("id", "status", "published", "updated_at")
        extra_kwargs: ClassVar[dict] = {"version": {"min_value": 1, "required": False}}

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {key: ["Unknown field."] for key in unknown}
            )
        if self.instance is not None and "version" not in attrs:
            raise serializers.ValidationError({"version": ["This field is required."]})
        fields = attrs.get(
            "attributes", self.instance.attributes if self.instance else []
        )
        if len({field["key"] for field in fields}) != len(fields):
            raise serializers.ValidationError(
                {"attributes": ["Attribute keys must be unique."]}
            )
        if self.instance and self.instance.published:
            old = {}
            for snapshot in self.instance.revisions.values_list("snapshot", flat=True):
                old.update({field["key"]: field for field in snapshot["attributes"]})
            for field in fields:
                previous = old.get(field["key"])
                if previous and (
                    field["type"] != previous["type"]
                    or field["unit"] != previous["unit"]
                ):
                    raise serializers.ValidationError(
                        {
                            "attributes": [
                                "Use a new key when changing an existing field's type or unit."
                            ]
                        }
                    )
        return attrs

    def create(self, validated_data):
        return save_draft(self.context["request"].user, validated_data)

    def update(self, instance, validated_data):
        return save_draft(self.context["request"].user, validated_data, instance)


class CategoryVersionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)


class CategoryRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryRevision
        fields = ("version", "snapshot", "created_at")
        read_only_fields = fields


class CategoryAuditSerializer(serializers.ModelSerializer):
    actor_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = CategoryAuditEvent
        fields = (
            "id",
            "action",
            "version",
            "actor_id",
            "before",
            "after",
            "created_at",
        )
        read_only_fields = fields


class TaxonomyCapabilitiesSerializer(serializers.Serializer):
    create = serializers.BooleanField()
    edit = serializers.BooleanField()
    publish = serializers.BooleanField()
    retire = serializers.BooleanField()
