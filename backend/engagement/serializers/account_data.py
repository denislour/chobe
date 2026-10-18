from rest_framework import serializers

from engagement.models import Favorite, SavedSearch, ShopFollow


class FavoriteSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ("listing_id", "created_at")
        read_only_fields = fields


class SavedSearchSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ("name", "filters", "active", "frequency", "created_at")
        read_only_fields = fields


class ShopFollowSnapshotSerializer(serializers.ModelSerializer):
    shop_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ShopFollow
        fields = ("shop_id", "created_at")
        read_only_fields = fields
