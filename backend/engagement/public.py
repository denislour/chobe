from engagement.models import Favorite


def favorite_listing_ids(user, listing_ids):
    if user is None or not user.is_authenticated:
        return set()
    return set(
        Favorite.objects.filter(user=user, listing_id__in=listing_ids).values_list(
            "listing_id", flat=True
        )
    )


def clear_listing_favorites(listing_id):
    Favorite.objects.filter(listing_id=listing_id).delete()
