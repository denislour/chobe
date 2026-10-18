import base64

from rest_framework import serializers

from shops.models import ShopAuditEvent
from shops.serializers.management import ShopPreviewSerializer


class ShopAuditSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopAuditEvent
        fields = ("action", "changes", "created_at")
        read_only_fields = fields


class ShopSnapshotSerializer(ShopPreviewSerializer):
    logo_jpeg_base64 = serializers.SerializerMethodField()
    banner_jpeg_base64 = serializers.SerializerMethodField()
    previous_slugs = serializers.SerializerMethodField()
    audit_events = ShopAuditSnapshotSerializer(many=True, read_only=True)

    class Meta(ShopPreviewSerializer.Meta):
        fields = (
            *ShopPreviewSerializer.Meta.fields,
            "logo_jpeg_base64",
            "banner_jpeg_base64",
            "previous_slugs",
            "audit_events",
        )
        read_only_fields = fields

    def get_logo_jpeg_base64(self, obj) -> str | None:
        return base64.b64encode(bytes(obj.logo)).decode() or None

    def get_banner_jpeg_base64(self, obj) -> str | None:
        return base64.b64encode(bytes(obj.banner)).decode() or None

    def get_previous_slugs(self, obj) -> list[str]:
        return list(obj.slugs.exclude(slug=obj.slug).values_list("slug", flat=True))
