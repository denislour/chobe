from rest_framework import serializers

from accounts.services.privacy import public_listing_phone
from categories.serializers.public import CategorySerializer
from listings.models import Favorite, Listing










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




