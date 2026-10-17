from datetime import timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import CommandError
from django.utils import timezone

from categories.services.attributes import validate_category_attributes
from listings.models import Listing, ListingImage
from listings.services.demo.moderation import seed_listing_story
from listings.services.images import process_listing_image
from listings.services.management import six_months_after

DEMO_PRODUCTS = {
    "demo_minh": (
        ("Pixel 6a, 128 GB, with case", "phones", 3200000, "phone"),
        ("Galaxy A54, 256 GB, small frame marks", "phones", 4100000, "phone"),
        ("iPhone 12, 128 GB, battery details available", "phones", 5200000, "phone"),
        ("Wireless headphones, complete set", "audio", 850000, "headphones"),
        ("Compact mechanical keyboard", "keyboards", 650000, "keyboard"),
        ("Phone for parts, draft condition notes", "phones", 450000, "phone"),
        ("Noise cancelling headphones", "audio", 1100000, "headphones"),
        ("Full-size keyboard, sold locally", "keyboards", 400000, "keyboard"),
        ("Travel phone with updated screen notes", "phones", 2800000, "phone"),
        ("USB keyboard, reviewed after clarification", "keyboards", 280000, "keyboard"),
    ),
    "demo_lan": (
        ("Fabric sofa, two seats", "seating", 2400000, "sofa"),
        ("Wooden reading chair", "seating", 650000, "chair"),
        ("Small wooden side table", "tables", 450000, "chair"),
        ("Desk lamp, warm light", "lighting", 220000, "lamp"),
        ("Office chair, wear needs clearer photos", "seating", 750000, "chair"),
        ("Living room lamp, unfinished draft", "lighting", 300000, "lamp"),
        ("Guest chair, temporarily hidden", "seating", 380000, "chair"),
        ("Reading lamp, sold", "lighting", 180000, "lamp"),
        ("Sofa with revised fabric condition", "seating", 1900000, "sofa"),
        ("Side chair with phone contact disabled", "seating", 350000, "chair"),
    ),
    "demo_huy": (
        (
            "Mirrorless camera body, shutter notes included",
            "cameras",
            6800000,
            "camera",
        ),
        ("Camera body with kit lens", "cameras", 8200000, "camera"),
        ("Compact camera for travel", "cameras", 1900000, "camera"),
        ("Backup camera body", "cameras", 4200000, "camera"),
        ("Camera lens, description needs correction", "cameras", 2100000, "camera"),
        ("Camera accessory bundle, draft", "cameras", 350000, "camera"),
        ("Camera grip, owner hidden", "cameras", 400000, "camera"),
        ("Entry-level camera, sold", "cameras", 2600000, "camera"),
        ("Camera with an unpublished title revision", "cameras", 5100000, "camera"),
        ("Travel camera, phone consent withdrawn", "cameras", 1750000, "camera"),
    ),
    "demo_thao": (
        ("Canvas tote bag, clean lining", "bags", 120000, "bag"),
        ("Everyday shoulder bag", "bags", 280000, "bag"),
        ("Light jacket, size M", "clothing", 190000, "shoes"),
        ("Weekend backpack, zip works", "bags", 230000, "bag"),
        ("Sports shoes, sizing description unclear", "sports-shoes", 350000, "shoes"),
        ("Clothing bundle, draft", "clothing", 150000, "bag"),
        ("Handbag kept for a friend", "bags", 200000, "bag"),
        ("Running shoes, sold", "sports-shoes", 300000, "shoes"),
        ("Bag temporarily held after a report", "bags", 420000, "bag"),
        ("Clothes bundle, price by discussion", "clothing", None, "bag"),
    ),
    "demo_duc": (
        ("City bicycle, serviced brakes", "bicycles", 1800000, "bicycle"),
        ("Weekend bicycle, medium frame", "bicycles", 2600000, "bicycle"),
        ("Running shoes, size 42", "sports-shoes", 450000, "shoes"),
        ("Commuter bike with rear rack", "bicycles", 2100000, "bicycle"),
        ("Bicycle with missing condition details", "bicycles", 1500000, "bicycle"),
        ("Cycling kit draft", "sports-shoes", 180000, "shoes"),
        ("Trail shoes, owner hidden", "sports-shoes", 380000, "shoes"),
        ("Student bicycle, sold", "bicycles", 1200000, "bicycle"),
        ("City bicycle due for availability renewal", "bicycles", 1600000, "bicycle"),
        ("Sports shoes to give away", "sports-shoes", 0, "shoes"),
    ),
    "demo_mai": (
        ("Three paperback novels", "fiction", 90000, "books"),
        ("Vietnamese short story collection", "fiction", 65000, "books"),
        ("English study workbook set", "study", 120000, "books"),
        ("Exam preparation books", "study", 150000, "books"),
        ("Book bundle with unclear edition notes", "study", 80000, "books"),
        ("New reading bundle, draft", "fiction", 70000, "books"),
        ("Books on hold, hidden by owner", "fiction", 100000, "books"),
        ("Language books, sold", "study", 110000, "books"),
        ("Old novel listing past its activity deadline", "fiction", 50000, "books"),
        ("Removed expired book listing", "fiction", 45000, "books"),
    ),
    "demo_linh": (
        ("Baby travel bag, clean and dry", "baby-gear", 180000, "baby"),
        ("Baby care starter bundle", "baby-gear", 240000, "baby"),
        ("Light stroller for short walks", "baby-gear", 850000, "baby"),
        ("Baby seat with complete straps", "baby-gear", 420000, "baby"),
        ("Baby item with missing age guidance", "baby-gear", 200000, "baby"),
        ("Baby clothes draft", "baby-gear", 90000, "baby"),
        ("Travel cot, temporarily hidden", "baby-gear", 650000, "baby"),
        ("Baby bath set, sold", "baby-gear", 150000, "baby"),
        ("Accessory in a retired demo category", "retired-category", 70000, "phone"),
        ("Baby listing deleted by its owner", "baby-gear", 80000, "baby"),
    ),
    "demo_bao": (
        ("Pet carrier bag, washable liner", "pet-accessories", 260000, "bag"),
        ("Pet travel bag, small size", "pet-accessories", 180000, "bag"),
        ("Foldable pet mat", "pet-accessories", 120000, "sofa"),
        ("Pet accessories bundle", "pet-accessories", 95000, "bag"),
        ("Carrier with incomplete size information", "pet-accessories", 160000, "bag"),
        ("Pet toy bundle draft", "pet-accessories", 60000, "bag"),
        ("Pet bag held by the owner", "pet-accessories", 140000, "bag"),
        ("Pet blanket, sold", "pet-accessories", 75000, "sofa"),
        ("Pet travel carrier, paused shop", "pet-accessories", 210000, "bag"),
        ("Pet supply giveaway, paused shop", "pet-accessories", 0, "bag"),
    ),
    "demo_an": (
        ("Coffee maker, cleaned after use", "kitchen", 750000, "coffee"),
        ("Compact coffee grinder", "kitchen", 420000, "coffee"),
        ("Electric kettle, 1.5 litre", "kitchen", 200000, "coffee"),
        ("Coffee equipment bundle", "kitchen", 1100000, "coffee"),
        ("Kitchen appliance with unclear wiring notes", "kitchen", 300000, "coffee"),
        ("Kitchen appliance draft", "kitchen", 150000, "coffee"),
        ("Coffee maker hidden by owner", "kitchen", 600000, "coffee"),
        ("Kitchen grinder, sold", "kitchen", 350000, "coffee"),
        ("Coffee maker in a suspended shop", "kitchen", 500000, "coffee"),
        ("Kitchen accessory bundle, suspended shop", "kitchen", 80000, "coffee"),
    ),
    "demo_nam": (
        ("Desk chair from a completed moving sale", "seating", 400000, "chair"),
        ("Two-seat sofa from a moving sale", "seating", 1600000, "sofa"),
        ("Reading lamp from a moving sale", "lighting", 150000, "lamp"),
        ("Side table from a moving sale", "tables", 250000, "chair"),
        ("Furniture listing rejected before closure", "seating", 300000, "chair"),
        ("Unfinished moving-sale draft", "tables", 200000, "chair"),
        ("Hidden chair from closed shop", "seating", 350000, "chair"),
        ("Sofa, sold before shop closure", "seating", 1400000, "sofa"),
        ("Old home item in a closed shop", "tables", 220000, "chair"),
        ("Books from a closed moving sale", "fiction", 60000, "books"),
    ),
}
DEMO_SPECIAL_STORIES = {
    "demo_minh": ("pending_edit", "reapproved"),
    "demo_lan": ("rejected_edit", "phone_hidden"),
    "demo_huy": ("draft_edit", "phone_withdrawn"),
    "demo_thao": ("report_hold", "negotiable"),
    "demo_duc": ("due_soon", "free"),
    "demo_mai": ("expired", "retention_deleted"),
    "demo_linh": ("retired_category", "owner_deleted"),
    "demo_bao": ("active", "free"),
    "demo_an": ("active", "active"),
    "demo_nam": ("active", "active"),
}


def product_attributes(category, index):
    values = {}
    hints = {
        "brand": ("Demo Goods", "Second Life", "Everyday")[index % 3],
        "storage_gb": (128, 256, 128)[index % 3],
        "material": ("fabric", "wood", "metal")[index % 3],
        "power_w": (800, 400, 1500)[index % 3],
        "size": ("M", "L", "42")[index % 3],
        "language": "Vietnamese" if index % 2 else "English",
        "age_months": (6, 12, 24)[index % 3],
    }
    for field in category.published["attributes"]:
        key = field["key"]
        value = hints.get(key)
        if value is None:
            kind = field["type"]
            if kind == "select":
                value = field["choices"][0]["value"]
            elif kind == "boolean":
                value = index % 2 == 0
            elif kind in ("number", "integer"):
                value = field["min_value"] if field["min_value"] is not None else 1
            else:
                value = "Demo value"
        values[key] = value
    return values


def seed_demo_listings(users, shops, categories):
    listings = {}
    assets = Path(__file__).resolve().parents[2] / "fixtures" / "demo"
    photos = {}
    now = timezone.now()
    for shop_index, (username, products) in enumerate(DEMO_PRODUCTS.items(), start=1):
        for index, (title, key, price, photo) in enumerate(products):
            pk = 1000 + shop_index * 100 + index + 1
            existing = Listing.objects.filter(pk=pk).first()
            if existing and existing.shop_id != shops[username].pk:
                raise CommandError(
                    f"Listing ID {pk} is already in use outside this demo dataset."
                )
            if existing:
                listings[(username, index)] = existing
                continue
            category = categories[key]
            if not category.published:
                raise CommandError(f"The demo listing category {key} is not published.")
            attributes = product_attributes(category, index)
            validate_category_attributes(
                category.pk, category.published["version"], attributes
            )
            story = (
                (
                    "active",
                    "active",
                    "active",
                    "pending",
                    "rejected",
                    "draft",
                    "hidden",
                    "sold",
                )[index]
                if index < 8
                else DEMO_SPECIAL_STORIES[username][index - 8]
            )
            created_at = now - timedelta(days=25 - index * 2, hours=shop_index)
            listing = Listing.objects.create(
                id=pk,
                shop=shops[username],
                category=category,
                title=f"[Demo] {title}",
                description=f"Demo seed v1. {title}. {('Unopened spare item; packaging has light shelf marks.' if index == 2 else 'Previously used; small cosmetic marks are described for the demo.')} Collection in {shops[username].area}; arrange a daytime inspection. Stock or illustrative photos only: the item, condition, price, seller and all interactions are fictional. Not offered for a real purchase.",
                condition="new" if index == 2 else "used",
                price_mode="free"
                if price == 0
                else "negotiable"
                if price is None or index == 1
                else "fixed",
                price=price,
                area=shops[username].area,
                attributes=attributes,
                schema_version=category.published["version"],
                phone_consent=story != "phone_hidden",
                rights_confirmed=story != "draft",
                last_owner_action_at=created_at,
                retention_due_at=six_months_after(created_at),
            )
            Listing.objects.filter(pk=pk).update(created_at=created_at)
            if story != "draft":
                if photo not in photos:
                    with (assets / f"{photo}.jpg").open("rb") as source:
                        data = source.read()
                    photos[photo] = process_listing_image(
                        SimpleUploadedFile(
                            f"{photo}.jpg", data, content_type="image/jpeg"
                        )
                    )
                for position in range(2 if index in (0, 1) else 1):
                    ListingImage.objects.create(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"chobe-demo-v1/listing/{pk}/image/{position}",
                        ),
                        listing=listing,
                        content=photos[photo],
                        position=position,
                    )
            seed_listing_story(listing, story, users, created_at)
            listings[(username, index)] = listing
    return listings
