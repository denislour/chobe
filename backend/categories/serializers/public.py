from rest_framework import serializers

from categories.serializers.attributes import AttributeDefinitionSerializer


class CategorySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    parent = serializers.UUIDField(read_only=True, allow_null=True)
    sort_order = serializers.IntegerField(read_only=True)
    version = serializers.IntegerField(read_only=True)
    attributes = AttributeDefinitionSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        return super().to_representation(instance.published)


class CategoryFacetsSerializer(serializers.Serializer):
    category_id = serializers.UUIDField()
    version = serializers.IntegerField()
    fields = AttributeDefinitionSerializer(many=True)


class CategoryValuesSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    attributes = serializers.DictField(child=serializers.JSONField())

    def validate_attributes(self, value):
        if len(value) > 30:
            raise serializers.ValidationError("Use at most 30 attribute values.")
        return value


class ValidatedCategoryValuesSerializer(CategoryValuesSerializer):
    category_id = serializers.UUIDField()
