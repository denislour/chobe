import re

from django.db.models.expressions import RawSQL
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from categories.services.publication import visible_categories
from listings.models import Listing


def public_listings():
    categories = list(visible_categories())
    return (
        Listing.objects.filter(
            status__in=("active", "pending", "rejected"),
            moderation_hold=False,
            shop__status="active",
            shop__owner__is_active=True,
            retention_due_at__gt=timezone.now(),
            published__category__in=categories,
        )
        .exclude(published={})
        .select_related("shop", "shop__owner")
    )


def search_listings(filters, queryset=None):
    queryset = public_listings() if queryset is None else queryset
    query = filters.get("q", "").strip().replace("đ", "d").replace("Đ", "D")
    if query:
        tokens = re.findall(r"[^\W_]+", query, re.UNICODE)[:12]
        if not tokens:
            return queryset.none()
        expression = " AND ".join(
            '"' + token.replace('"', '""') + '"*' for token in tokens
        )
        queryset = queryset.filter(
            pk__in=RawSQL(
                "SELECT rowid FROM listings_search WHERE listings_search MATCH %s",
                [expression],
            )
        )
    category = filters.get("category")
    if category:
        snapshots = visible_categories()
        category = str(category)
        if category not in snapshots:
            return queryset.none()
        descendants = {category}
        for _ in range(4):
            descendants.update(
                key
                for key, value in snapshots.items()
                if value.get("parent") in descendants
            )
        queryset = queryset.filter(published__category__in=list(descendants))
    for field in ("condition", "shop"):
        if filters.get(field):
            key = "shop_id" if field == "shop" else "published__condition"
            queryset = queryset.filter(**{key: filters[field]})
    if filters.get("location"):
        queryset = queryset.filter(published__area__iexact=filters["location"])
    if filters.get("price_min") is not None:
        queryset = queryset.filter(published__price__gte=filters["price_min"])
    if filters.get("price_max") is not None:
        queryset = queryset.filter(published__price__lte=filters["price_max"])
    attributes = filters.get("attributes", {})
    if attributes:
        snapshot = visible_categories().get(str(category))
        if snapshot is None:
            raise ValidationError(
                {"attributes": ["Choose a category before filtering attributes."]}
            )
        definitions = {
            item["key"]: item for item in snapshot["attributes"] if item["filterable"]
        }
        for key, value in attributes.items():
            field = definitions.get(key)
            if field is None:
                raise ValidationError(
                    {"attributes": ["Choose a supported category filter."]}
                )
            kind = field["type"]
            valid = {
                "boolean": type(value) is bool,
                "integer": type(value) is int,
                "number": type(value) in (int, float),
                "text": isinstance(value, str),
                "select": isinstance(value, str)
                and value in {choice["value"] for choice in field["choices"]},
            }[kind]
            if not valid:
                raise ValidationError(
                    {"attributes": [f"Enter a valid filter for {key}."]}
                )
            queryset = queryset.filter(**{f"published__attributes__{key}": value})
    ordering = {
        "newest": ("-published_at", "-pk"),
        "price_asc": ("published__price", "-pk"),
        "price_desc": ("-published__price", "-pk"),
    }
    return queryset.order_by(*ordering[filters.get("sort", "newest")])
