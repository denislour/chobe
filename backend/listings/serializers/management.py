from typing import ClassVar

from rest_framework import serializers

from categories.models import Category
from categories.services.publication import visible_categories
from listings.models import Listing, ListingAuditEvent
from listings.services.management import (
    save_draft,
)


class ListingDraftSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), allow_null=True, required=False
    )
    images = serializers.SerializerMethodField()
    published = serializers.JSONField(read_only=True)

    class Meta:
        model = Listing
        fields = (
            "id",
            "category",
            "title",
            "description",
            "condition",
            "price_mode",
            "price",
            "area",
            "attributes",
            "schema_version",
            "phone_consent",
            "rights_confirmed",
            "status",
            "version",
            "submitted_version",
            "moderation_hold",
            "published",
            "images",
            "last_owner_action_at",
            "retention_due_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "submitted_version",
            "moderation_hold",
            "last_owner_action_at",
            "retention_due_at",
            "created_at",
            "updated_at",
        )
        extra_kwargs: ClassVar[dict] = {
            "version": {"required": False, "min_value": 1},
            "schema_version": {"min_value": 1},
            "price": {"max_value": 10**15},
        }

    def get_images(self, instance) -> list[dict]:
        return [
            {
                "id": str(image.pk),
                "url": f"/api/v1/me/listings/{instance.pk}/image/{image.pk}/",
            }
            for image in instance.images.filter(attached=True)
        ]

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {key: ["Unknown field."] for key in unknown}
            )
        if self.instance and "version" not in attrs:
            raise serializers.ValidationError({"version": ["This field is required."]})
        if not self.instance:
            attrs.pop("version", None)
        category = attrs.get("category")
        if category and str(category.pk) not in visible_categories():
            raise serializers.ValidationError(
                {"category": ["Choose an active category."]}
            )
        values = attrs.get("attributes", {})
        if not isinstance(values, dict) or len(values) > 30:
            raise serializers.ValidationError(
                {"attributes": ["Use an object with up to 30 attributes."]}
            )
        mode = attrs.get("price_mode", getattr(self.instance, "price_mode", "fixed"))
        price = attrs.get("price", getattr(self.instance, "price", None))
        if mode == "free" and price not in (None, 0):
            raise serializers.ValidationError(
                {"price": ["A free item cannot have a price."]}
            )
        return attrs

    def create(self, validated_data):
        return save_draft(self.context["request"].user, validated_data)

    def update(self, instance, validated_data):
        return save_draft(self.context["request"].user, validated_data, instance)


class ListingVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = ("version",)
        extra_kwargs: ClassVar[dict] = {"version": {"required": True, "min_value": 1}}


class ListingStatusSerializer(ListingVersionSerializer):
    status = serializers.ChoiceField(choices=("active", "hidden", "sold"))

    class Meta(ListingVersionSerializer.Meta):
        fields = ("version", "status")


class ImageUploadSerializer(ListingVersionSerializer):
    image = serializers.FileField(write_only=True)

    class Meta(ListingVersionSerializer.Meta):
        fields = ("version", "image")


class ImageOrderSerializer(ListingVersionSerializer):
    images = serializers.ListField(child=serializers.UUIDField(), max_length=10)

    class Meta(ListingVersionSerializer.Meta):
        fields = ("version", "images")


class AppealSerializer(ListingVersionSerializer):
    reason = serializers.CharField(max_length=2000)

    class Meta(ListingVersionSerializer.Meta):
        fields = ("version", "reason")


class ListingAuditSerializer(serializers.ModelSerializer):
    actor_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = ListingAuditEvent
        fields = (
            "id",
            "actor_id",
            "action",
            "source",
            "version",
            "reason",
            "created_at",
        )
