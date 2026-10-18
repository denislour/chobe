import base64
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from accounts.models import ConsentEvent, PrivacySettings, Profile, User, ViewingHistory
from engagement.serializers.account_data import (
    FavoriteSnapshotSerializer,
    SavedSearchSnapshotSerializer,
    ShopFollowSnapshotSerializer,
)
from listings.models import (
    Favorite,
    Listing,
    NotificationPreference,
    Report,
    SavedSearch,
)
from listings.serializers.account_data import ListingSnapshotSerializer
from moderation.serializers.account_data import ReportSnapshotSerializer
from notifications.account_data import NotificationPreferenceSnapshotSerializer
from shops.models import Shop
from shops.serializers.account_data import ShopSnapshotSerializer


class AccountSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "date_joined")
        read_only_fields = fields


class ProfileSnapshotSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Profile
        fields = (
            "display_name",
            "area",
            "bio",
            "phone",
            "email",
            "username",
            "version",
            "updated_at",
        )
        read_only_fields = fields


class PrivacySnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacySettings
        fields = (
            "share_phone",
            "record_history",
            "consent_at",
            "version",
            "updated_at",
        )
        read_only_fields = fields


class ConsentSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentEvent
        fields = ("share_phone", "policy_version", "created_at")
        read_only_fields = fields


class HistorySnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewingHistory
        fields = ("listing_id", "viewed_at")
        read_only_fields = fields


class AccountDataSnapshotSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField(default=timezone.now, read_only=True)
    account = AccountSnapshotSerializer(source="*", read_only=True)
    profile = ProfileSnapshotSerializer(read_only=True)
    avatar_jpeg_base64 = serializers.SerializerMethodField()
    privacy = PrivacySnapshotSerializer(read_only=True)
    consent = ConsentSnapshotSerializer(
        source="consentevent_set", many=True, read_only=True
    )
    viewing_history = serializers.SerializerMethodField()
    shop = serializers.SerializerMethodField()
    listings = serializers.SerializerMethodField()
    favorites = serializers.SerializerMethodField()
    saved_searches = serializers.SerializerMethodField()
    reports = serializers.SerializerMethodField()
    notification_preferences = serializers.SerializerMethodField()
    followed_shops = ShopFollowSnapshotSerializer(
        source="shop_follows", many=True, read_only=True
    )

    def get_avatar_jpeg_base64(self, user) -> str | None:
        return base64.b64encode(bytes(user.profile.avatar)).decode() or None

    def get_viewing_history(self, user) -> list:
        history = user.viewinghistory_set.filter(
            viewed_at__gte=timezone.now() - timedelta(days=30)
        )[:100]
        return HistorySnapshotSerializer(history, many=True).data

    def get_shop(self, user) -> dict | None:
        shop = Shop.objects.filter(owner=user).first()
        return ShopSnapshotSerializer(shop).data if shop is not None else None

    def get_listings(self, user) -> list:
        return ListingSnapshotSerializer(
            Listing.objects.filter(shop__owner=user).exclude(status="deleted"),
            many=True,
        ).data

    def get_favorites(self, user) -> list:
        return FavoriteSnapshotSerializer(
            Favorite.objects.filter(user=user), many=True
        ).data

    def get_saved_searches(self, user) -> list:
        return SavedSearchSnapshotSerializer(
            SavedSearch.objects.filter(user=user), many=True
        ).data

    def get_reports(self, user) -> list:
        return ReportSnapshotSerializer(
            Report.objects.filter(reporter=user), many=True
        ).data

    def get_notification_preferences(self, user) -> dict | None:
        preferences = NotificationPreference.objects.filter(user=user).first()
        return (
            NotificationPreferenceSnapshotSerializer(preferences).data
            if preferences
            else None
        )
