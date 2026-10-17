from rest_framework import serializers

from accounts.services.privacy import public_listing_phone
from categories.serializers.public import CategorySerializer
from listings.models import Favorite, Listing


class ListingSearchSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=160, required=False, allow_blank=True)
    category = serializers.UUIDField(required=False)
    shop = serializers.UUIDField(required=False)
    location = serializers.CharField(max_length=120, required=False, allow_blank=True)
    price_min = serializers.IntegerField(min_value=0, max_value=10**15, required=False)
    price_max = serializers.IntegerField(min_value=0, max_value=10**15, required=False)
    condition = serializers.ChoiceField(choices=Listing.Condition, required=False)
    sort = serializers.ChoiceField(
        choices=("newest", "price_asc", "price_desc"), required=False
    )
    attributes = serializers.JSONField(required=False)
    page = serializers.IntegerField(min_value=1, max_value=1000, required=False)

    def validate(self, attrs):
        if len(str(self.initial_data)) > 6000:
            raise serializers.ValidationError("The search filters are too long.")
        if set(self.initial_data) - set(self.fields):
            raise serializers.ValidationError("Use only supported search filters.")
        if attrs.get("price_min", 0) > attrs.get("price_max", 9223372036854775807):
            raise serializers.ValidationError(
                {"price_max": ["The maximum must be at least the minimum."]}
            )
        values = attrs.get("attributes", {})
        if not isinstance(values, dict) or len(values) > 30:
            raise serializers.ValidationError(
                {"attributes": ["Use up to 30 attribute filters."]}
            )
        if any(
            not key.isidentifier() or key in ("constructor", "prototype") or "__" in key
            for key in values
        ):
            raise serializers.ValidationError(
                {"attributes": ["Use supported attribute keys."]}
            )
        if any(type(value) not in (str, int, float, bool) for value in values.values()):
            raise serializers.ValidationError(
                {"attributes": ["Use scalar attribute values."]}
            )
        return attrs








class ListingPublicSerializer(serializers.ModelSerializer):
    category = serializers.UUIDField(read_only=True)
    category_schema = CategorySerializer(read_only=True)
    shop = ListingShopSerializer(read_only=True)
    images = PublicImageSerializer(many=True, read_only=True)
    phone = serializers.CharField(read_only=True, allow_null=True)
    is_favorite = serializers.BooleanField(read_only=True)

    class Meta:
        model = Listing
        list_serializer_class = PublicListingListSerializer
        fields = (
            "id",
            "title",
            "description",
            "condition",
            "price_mode",
            "price",
            "area",
            "category",
            "category_schema",
            "attributes",
            "schema_version",
            "version",
            "published_at",
            "shop",
            "images",
            "phone",
            "is_favorite",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        snapshot = instance.published
        shop = instance.shop
        fields = (
            "title",
            "description",
            "condition",
            "price_mode",
            "price",
            "area",
            "category",
            "attributes",
            "schema_version",
            "version",
        )
        result = {key: snapshot[key] for key in fields}
        request = self.context.get("request")
        user = getattr(request, "user", None)
        favorite_ids = self.context.get("favorite_ids")
        phone_numbers = self.context.get("phone_numbers")
        favorite = (
            instance.pk in favorite_ids
            if favorite_ids is not None
            else bool(
                user
                and user.is_authenticated
                and Favorite.objects.filter(user=user, listing=instance).exists()
            )
        )
        phone = (
            (phone_numbers.get(shop.owner_id) or None)
            if phone_numbers is not None
            else public_listing_phone(shop.owner, is_public_listing=True)
        )
        result.update(
            id=instance.pk,
            published_at=instance.published_at,
            is_favorite=favorite,
            category_schema=snapshot["category_schema"],
            shop={"id": str(shop.pk), "name": shop.name, "slug": shop.slug},
            images=[
                {"id": pk, "url": f"/api/v1/listings/{instance.pk}/image/{pk}/"}
                for pk in snapshot["images"]
            ],
            phone=phone
            if snapshot.get("phone_consent") and instance.phone_consent
            else None,
        )
        return result


class ContactEventSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("call", "copy"))


class CompareQuerySerializer(serializers.Serializer):
    ids = serializers.CharField(max_length=80)

    def validate_ids(self, value):
        try:
            ids = [int(item) for item in value.split(",")]
        except ValueError as error:
            raise serializers.ValidationError(
                "Use listing IDs separated by commas."
            ) from error
        if (
            not 1 <= len(ids) <= 3
            or len(ids) != len(set(ids))
            or any(pk < 1 or pk > 9223372036854775807 for pk in ids)
        ):
            raise serializers.ValidationError(
                "Choose between one and three different listings."
            )
        return ids
