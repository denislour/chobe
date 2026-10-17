from rest_framework import serializers
from rest_framework.fields import empty


class AttributeChoiceSerializer(serializers.Serializer):
    value = serializers.RegexField(r"^[a-z0-9][a-z0-9_-]{0,39}$")
    label = serializers.CharField(max_length=80)

    def to_internal_value(self, data):
        if isinstance(data, dict) and set(data) - set(self.fields):
            raise serializers.ValidationError("Unknown choice fields.")
        return super().to_internal_value(data)


class AttributeDefinitionSerializer(serializers.Serializer):
    key = serializers.RegexField(
        r"^(?!(?:constructor|prototype)$)[a-z][a-z0-9_]{0,39}$"
    )
    label = serializers.CharField(max_length=80)
    type = serializers.ChoiceField(
        choices=("text", "integer", "number", "boolean", "select")
    )
    required = serializers.BooleanField(default=False)
    filterable = serializers.BooleanField(default=False)
    unit = serializers.CharField(max_length=16, allow_blank=True, default="")
    choices = AttributeChoiceSerializer(many=True, max_length=50, default=list)
    min_value = serializers.FloatField(required=False, allow_null=True, default=None)
    max_value = serializers.FloatField(required=False, allow_null=True, default=None)
    max_length = serializers.IntegerField(min_value=1, max_value=1000, default=200)

    def run_validation(self, data=empty):
        # Definitions are complete replacements, including inside a category PATCH.
        if self.root.partial:
            serializer = type(self)(data=data, context=self.context)
            serializer.is_valid(raise_exception=True)
            return serializer.validated_data
        return super().run_validation(data)

    def to_internal_value(self, data):
        if isinstance(data, dict) and set(data) - set(self.fields):
            raise serializers.ValidationError("Unknown attribute definition fields.")
        return super().to_internal_value(data)

    def validate(self, attrs):
        choices = attrs["choices"]
        if attrs["type"] == "select":
            if not choices or len({item["value"] for item in choices}) != len(choices):
                raise serializers.ValidationError(
                    {"choices": ["Provide unique choices for this field."]}
                )
        elif choices:
            raise serializers.ValidationError(
                {"choices": ["Choices are only used by select fields."]}
            )
        minimum, maximum = attrs["min_value"], attrs["max_value"]
        if attrs["type"] not in ("integer", "number") and (
            minimum is not None or maximum is not None or attrs["unit"]
        ):
            raise serializers.ValidationError(
                "Only numeric fields can have bounds or a unit."
            )
        if minimum is not None and maximum is not None and minimum > maximum:
            raise serializers.ValidationError("The minimum cannot exceed the maximum.")
        return attrs
