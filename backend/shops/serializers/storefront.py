from django.urls import reverse
from rest_framework import serializers

from shops.models import Shop


class StorefrontSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()
    is_following = serializers.BooleanField(read_only=True, default=False)

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
            "created_at",
            "is_following",
        )
        read_only_fields = fields

    def get_logo_url(self, obj) -> str | None:
        return self.image_url(obj, "logo")

    def get_banner_url(self, obj) -> str | None:
        return self.image_url(obj, "banner")

    def image_url(self, obj, kind):
        if not getattr(obj, kind):
            return None
        path = reverse("storefront-image", kwargs={"slug": obj.slug, "kind": kind})
        return f"{path}?version={obj.version}"
