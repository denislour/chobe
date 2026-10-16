from typing import ClassVar
from urllib.parse import urlsplit

from django.urls import reverse
from rest_framework import serializers

from shops.models import Shop, ShopSlug
from shops.services.images import process_shop_image_upload
from shops.services.management import create_shop, update_shop


class ShopPreviewSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()

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
            "logo_url",
            "banner_url",
            "status",
            "version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_logo_url(self, obj) -> str | None:
        return self.image_url(obj, "logo")

    def get_banner_url(self, obj) -> str | None:
        return self.image_url(obj, "banner")

    def image_url(self, obj, kind):
        if not getattr(obj, kind):
            return None
        path = reverse("shop-image", kwargs={"pk": obj.pk, "kind": kind})
        return f"{path}?version={obj.version}"


class ShopSerializer(ShopPreviewSerializer):
    slug = serializers.RegexField(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    logo = serializers.FileField(write_only=True, required=False)
    banner = serializers.FileField(write_only=True, required=False)
    remove_logo = serializers.BooleanField(write_only=True, required=False)
    remove_banner = serializers.BooleanField(write_only=True, required=False)

    class Meta(ShopPreviewSerializer.Meta):
        fields = (
            *ShopPreviewSerializer.Meta.fields,
            "logo",
            "banner",
            "remove_logo",
            "remove_banner",
        )
        read_only_fields = ("id", "status", "created_at", "updated_at")
        extra_kwargs: ClassVar[dict] = {"version": {"min_value": 1, "required": False}}

    def validate_slug(self, value):
        if value in {"admin", "api", "me", "new", "preview", "status"}:
            raise serializers.ValidationError("Choose a different shop address.")
        aliases = ShopSlug.objects.filter(slug=value)
        if self.instance is not None:
            aliases = aliases.exclude(shop=self.instance)
        if aliases.exists():
            raise serializers.ValidationError("This shop address is already in use.")
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

    def validate_logo(self, value):
        return process_shop_image_upload(value, bounds=(512, 512))

    def validate_banner(self, value):
        return process_shop_image_upload(value, bounds=(1600, 900))

    def validate(self, attrs):
        if self.instance is not None and "version" not in attrs:
            raise serializers.ValidationError({"version": ["This field is required."]})
        for field in ("logo", "banner"):
            if attrs.get(f"remove_{field}") and field in attrs:
                raise serializers.ValidationError(
                    {field: ["Choose upload or removal, not both."]}
                )
        return attrs

    def create(self, validated_data):
        values = validated_data.copy()
        values.pop("version", None)
        values.pop("remove_logo", None)
        values.pop("remove_banner", None)
        return create_shop(self.context["request"].user, values)

    def update(self, instance, validated_data):
        return update_shop(instance, self.context["request"].user, validated_data)


class ShopStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("active", "paused", "closed"))
    version = serializers.IntegerField(min_value=1, max_value=2**63 - 1)
