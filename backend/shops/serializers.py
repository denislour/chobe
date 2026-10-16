from typing import ClassVar
from urllib.parse import urlsplit

from rest_framework import serializers

from shops.models import Shop, ShopAuditEvent, ShopSlug
from shops.services.management import create_shop, update_shop


class ShopPreviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "area",
            "contact_hours",
            "website_url",
            "social_url",
            "status",
            "version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields



class ShopSerializer(ShopPreviewSerializer):
    slug = serializers.RegexField(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    class Meta(ShopPreviewSerializer.Meta):
        read_only_fields = ("id", "status", "created_at", "updated_at")
        extra_kwargs: ClassVar[dict] = {"version": {"min_value": 1, "required": False}}

    def validate_slug(self, value):
        if value in {"admin", "api", "me", "new", "preview", "status"}:
            raise serializers.ValidationError("Choose a different shop address.")
        return value

    def validate_website_url(self, value):
        return self.validate_link(value)

    def validate_social_url(self, value):
        return self.validate_link(value)

    def validate_link(self, value):
        if value:
            parts = urlsplit(value)
            if (
                parts.scheme not in {"http", "https"}
                or parts.username
                or parts.password
            ):
                raise serializers.ValidationError(
                    "Use an HTTP or HTTPS link without credentials."
                )
        return value

    def validate(self, attrs):
        if self.instance is not None and "version" not in attrs:
            raise serializers.ValidationError({"version": ["This field is required."]})
        return attrs

    def create(self, validated_data):
        values = validated_data.copy()
        values.pop("version", None)
        return create_shop(self.context["request"].user, values)

    def update(self, instance, validated_data):
        return update_shop(instance, self.context["request"].user, validated_data)
