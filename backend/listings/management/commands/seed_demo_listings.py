from collections import Counter
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.management.commands.seed_demo_accounts import (
    DEMO_PASSWORD,
    DEMO_PEOPLE,
    demo_accounts,
)
from accounts.models import AccountDataExport, DeletionRequest, ViewingHistory
from categories.management.commands.seed_demo_categories import demo_categories
from categories.services.attributes import validate_category_attributes
from categories.services.publication import retire_category
from discovery.queries import public_listings
from listings.models import (
    Favorite,
    Listing,
    ListingAuditEvent,
    ListingImage,
    ListingMetric,
    ListingRevision,
    ModerationCase,
    Notification,
    NotificationPreference,
    Report,
    ReportDecision,
    SavedSearch,
)
from listings.services.images import process_listing_image
from listings.services.management import draft_snapshot, erase_listing, six_months_after
from shops.management.commands.seed_demo_shops import demo_shops
from shops.models import ShopFollow


def story_event(listing, actor, action, when, reason=""):
    event = ListingAuditEvent.objects.create(
        listing=listing,
        actor=actor,
        action=action,
        version=listing.version,
        reason=reason,
        source="manual",
    )
    ListingAuditEvent.objects.filter(pk=event.pk).update(created_at=when)


def submitted_revision(listing, when):
    listing.submitted_version = listing.version
    snapshot = draft_snapshot(listing)
    snapshot["category_schema"] = deepcopy(listing.category.published)
    revision = ListingRevision.objects.create(
        listing=listing, version=listing.version, snapshot=snapshot
    )
    ListingRevision.objects.filter(pk=revision.pk).update(created_at=when)
    case = ModerationCase.objects.create(revision=revision)
    ModerationCase.objects.filter(pk=case.pk).update(created_at=when, updated_at=when)
    story_event(listing, listing.shop.owner, "submitted", when)
    return revision, case


@transaction.atomic
def seed_listing_story(listing, story, users, created_at):
    if not settings.DEMO_MODE:
        raise CommandError("Set DJANGO_DEMO_MODE=true before seeding demo data.")
    owner = listing.shop.owner
    moderator = users["demo_moderator"]
    now = timezone.now()
    if story in ("due_soon", "expired", "retention_deleted"):
        created_at = now - timedelta(days=190 if story == "due_soon" else 215)
        ListingRevision.objects.filter(listing=listing).delete()
        type(listing).objects.filter(pk=listing.pk).update(created_at=created_at)
        listing.last_owner_action_at = now - timedelta(
            days=175 if story == "due_soon" else 200
        )
        listing.retention_due_at = six_months_after(listing.last_owner_action_at)
    story_event(listing, owner, "draft_saved", created_at)
    if story == "draft":
        listing.description = ""
        listing.rights_confirmed = False
        listing.save()
        return
    for index, image in enumerate(listing.images.all()):
        listing.version += 1
        story_event(
            listing, owner, "image_added", created_at + timedelta(minutes=15 + index)
        )
    listing.version += 1
    revision, case = submitted_revision(listing, created_at + timedelta(hours=1))
    listing.status = "pending"
    if story == "pending":
        listing.save()
        return
    rejected = story == "rejected"
    listing.version += 1
    case.status = "rejected" if rejected else "approved"
    case.reason = (
        "Demo manual review: add clearer wear photos and explain the item condition."
        if rejected
        else "Demo manual review: the submitted details and photo rights confirmation are acceptable."
    )
    case.version += 1
    case.save()
    ModerationCase.objects.filter(pk=case.pk).update(
        updated_at=created_at + timedelta(hours=2)
    )
    story_event(
        listing,
        moderator,
        "reject" if rejected else "approve",
        created_at + timedelta(hours=2),
        case.reason,
    )
    listing.status = "rejected" if rejected else "active"
    if not rejected:
        listing.published = deepcopy(revision.snapshot)
        listing.published_at = created_at + timedelta(hours=2)
    if rejected and owner.username in ("demo_minh", "demo_thao", "demo_linh"):
        case.appeal = "Demo appeal: I can provide clearer details. Please review the condition notes again."
        case.appeal_open = True
        case.version += 1
        case.save()
        story_event(
            listing, owner, "appealed", created_at + timedelta(hours=3), case.appeal
        )
    if story in ("hidden", "sold", "report_hold"):
        listing.status = "sold" if story == "sold" else "hidden"
        listing.moderation_hold = story == "report_hold"
        listing.submitted_version = None
        listing.version += 1
        story_event(
            listing,
            moderator if story == "report_hold" else owner,
            "report_hidden" if story == "report_hold" else f"status_{listing.status}",
            created_at + timedelta(hours=3),
            "Demo report action: temporarily hidden pending clarification."
            if story == "report_hold"
            else "",
        )
    if story in ("pending_edit", "rejected_edit", "draft_edit"):
        listing.version += 1
        listing.title += " — revised draft"
        listing.description += (
            " Unpublished update: the owner is clarifying a small condition detail."
        )
        listing.submitted_version = None
        story_event(listing, owner, "draft_saved", created_at + timedelta(days=1))
        if story != "draft_edit":
            listing.version += 1
            _, edited_case = submitted_revision(
                listing, created_at + timedelta(days=1, hours=1)
            )
            listing.status = "pending"
            if story == "rejected_edit":
                listing.version += 1
                listing.status = "rejected"
                edited_case.status = "rejected"
                edited_case.reason = "Demo manual review: clarify the revised condition statement. The previous approved version remains public."
                edited_case.version += 1
                edited_case.save()
                story_event(
                    listing,
                    moderator,
                    "reject",
                    created_at + timedelta(days=1, hours=2),
                    edited_case.reason,
                )
    if story == "reapproved":
        listing.published = {}
        listing.status = "rejected"
        listing.version += 1
        case.status = "rejected"
        case.reason = "Demo re-review: initial condition notes needed clarification."
        case.version += 1
        case.save()
        story_event(
            listing, moderator, "reject", created_at + timedelta(hours=3), case.reason
        )
        case.appeal = "Demo appeal: the original notes include the requested details."
        case.appeal_open = True
        case.version += 1
        case.save()
        story_event(
            listing, owner, "appealed", created_at + timedelta(hours=4), case.appeal
        )
        case.status = "approved"
        case.reason = "Demo appeal reviewed manually; this exact submitted snapshot is approved again."
        case.appeal_open = False
        case.version += 1
        case.save()
        listing.version += 1
        listing.status = "active"
        listing.published = deepcopy(revision.snapshot)
        listing.published_at = created_at + timedelta(hours=5)
        story_event(
            listing, moderator, "approve", created_at + timedelta(hours=5), case.reason
        )
    if story == "phone_withdrawn":
        listing.published["phone_consent"] = True
        listing.phone_consent = False
        listing.version += 1
        story_event(
            listing,
            owner,
            "draft_saved",
            created_at + timedelta(hours=3),
            "Demo: per-listing phone consent withdrawn.",
        )
    listing.save()
    if story in ("owner_deleted", "retention_deleted"):
        erase_listing(
            listing,
            owner if story == "owner_deleted" else None,
            "owner_deleted" if story == "owner_deleted" else "retention_deleted",
        )


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


@transaction.atomic
def seed_demo_listings(users, shops, categories):
    if not settings.DEMO_MODE:
        raise CommandError("Set DJANGO_DEMO_MODE=true before seeding demo data.")
    listings = {}
    assets = settings.BASE_DIR / "listings" / "fixtures" / "demo"
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


DEMO_FAVORITES = {
    "demo_minh": (("demo_lan", 0), ("demo_huy", 0)),
    "demo_lan": (("demo_mai", 0), ("demo_linh", 0)),
    "demo_huy": (("demo_minh", 0), ("demo_duc", 0)),
    "demo_thao": (("demo_lan", 1), ("demo_mai", 1)),
    "demo_duc": (("demo_huy", 1), ("demo_bao", 0)),
    "demo_mai": (("demo_linh", 0), ("demo_lan", 0)),
    "demo_linh": (("demo_mai", 0), ("demo_bao", 1)),
    "demo_bao": (("demo_duc", 1),),
    "demo_an": (("demo_minh", 1),),
    "demo_nam": (("demo_lan", 0),),
    "demo_ha": (("demo_minh", 0), ("demo_minh", 1), ("demo_mai", 0), ("demo_duc", 7)),
    "demo_quang": (("demo_lan", 0), ("demo_lan", 1), ("demo_duc", 0), ("demo_thao", 8)),
    "demo_vy": (("demo_huy", 0), ("demo_linh", 0)),
    "demo_tuan": (("demo_thao", 0), ("demo_bao", 0), ("demo_an", 0), ("demo_duc", 9)),
    "demo_trang": (),
}
DEMO_SEARCHES = (
    (
        "demo_ha",
        "Phones under 5 million",
        {"category": "phones", "price_max": 5000000},
        "immediate",
        True,
    ),
    (
        "demo_ha",
        "Reading on a budget",
        {"category": "fiction", "price_max": 100000},
        "daily",
        True,
    ),
    (
        "demo_quang",
        "Furniture for the new room",
        {"category": "seating", "price_max": 2500000},
        "daily",
        True,
    ),
    (
        "demo_quang",
        "Used city bicycles",
        {"category": "bicycles", "condition": "used"},
        "immediate",
        True,
    ),
    (
        "demo_vy",
        "Camera shortlist without email",
        {"category": "cameras", "price_max": 9000000},
        "daily",
        True,
    ),
    (
        "demo_tuan",
        "Free items nearby",
        {"price_min": 0, "price_max": 0},
        "immediate",
        True,
    ),
    (
        "demo_tuan",
        "Paused bag search",
        {"category": "bags", "price_max": 300000},
        "daily",
        False,
    ),
    ("demo_minh", "Camera gear to browse", {"category": "cameras"}, "daily", True),
    ("demo_lan", "Books for a quiet evening", {"category": "fiction"}, "daily", True),
    (
        "demo_huy",
        "Second-hand phones",
        {"category": "phones", "condition": "used"},
        "immediate",
        True,
    ),
    (
        "demo_duc",
        "Camera gear for trips",
        {"category": "cameras", "price_max": 7000000},
        "daily",
        True,
    ),
    ("demo_mai", "Baby supplies to browse", {"category": "baby-gear"}, "daily", True),
    ("demo_linh", "Reading for the family", {"category": "fiction"}, "daily", True),
)


@transaction.atomic
def seed_demo_engagement(users, listings, categories):
    if not settings.DEMO_MODE:
        raise CommandError("Set DJANGO_DEMO_MODE=true before seeding demo data.")
    now = timezone.now()
    for username, user in users.items():
        inbox = username in (
            "demo_ha",
            "demo_quang",
            "demo_tuan",
            "demo_minh",
            "demo_lan",
            "demo_huy",
            "demo_duc",
            "demo_mai",
            "demo_linh",
        )
        email = username in ("demo_ha", "demo_lan")
        NotificationPreference.objects.get_or_create(
            user=user,
            defaults={"inbox": inbox, "email": email, "version": 2 if inbox else 1},
        )
        for index, target in enumerate(DEMO_FAVORITES.get(username, ())):
            favorite, created = Favorite.objects.get_or_create(
                user=user, listing=listings[target]
            )
            if created:
                Favorite.objects.filter(pk=favorite.pk).update(
                    created_at=min(
                        now - timedelta(days=2, hours=index),
                        listings[target].published_at + timedelta(minutes=20),
                    )
                )
        if (
            user.is_active
            and user.privacy.record_history
            and username in DEMO_FAVORITES
        ):
            targets = list(DEMO_FAVORITES[username]) + [
                ("demo_minh", 2),
                ("demo_mai", 1),
            ]
            for index, target in enumerate(dict.fromkeys(targets)):
                entry, created = ViewingHistory.objects.get_or_create(
                    user=user, listing_id=listings[target].pk
                )
                if created:
                    ViewingHistory.objects.filter(pk=entry.pk).update(
                        viewed_at=min(
                            now - timedelta(hours=2 + index),
                            listings[target].published_at + timedelta(minutes=25),
                        )
                        if listings[target].status in ("hidden", "sold")
                        or listings[target].shop.status != "active"
                        else now - timedelta(hours=2 + index)
                    )
    searches = {}
    for username, name, filters, frequency, active in DEMO_SEARCHES:
        values = dict(filters)
        if "category" in values:
            values["category"] = str(categories[values["category"]].pk)
        search, created = SavedSearch.objects.get_or_create(
            user=users[username],
            name=f"[Demo] {name}",
            defaults={"filters": values, "frequency": frequency, "active": active},
        )
        if created:
            SavedSearch.objects.filter(pk=search.pk).update(
                created_at=now - timedelta(days=40)
            )
        searches[(username, name)] = search
    notifications = (
        ("demo_ha", "Phones under 5 million", ("demo_minh", 0), False, "blocked"),
        ("demo_ha", "Phones under 5 million", ("demo_minh", 1), True, "blocked"),
        ("demo_ha", "Reading on a budget", ("demo_mai", 0), False, "failed"),
        ("demo_ha", "Phones under 5 million", ("demo_minh", 8), False, "queued"),
        ("demo_ha", "Reading on a budget", ("demo_mai", 1), False, "sending"),
        ("demo_lan", "Books for a quiet evening", ("demo_mai", 1), True, "sent"),
        ("demo_quang", "Furniture for the new room", ("demo_lan", 0), False, "blocked"),
        ("demo_quang", "Furniture for the new room", ("demo_lan", 1), True, "blocked"),
        ("demo_quang", "Used city bicycles", ("demo_duc", 0), False, "blocked"),
        ("demo_quang", "Furniture for the new room", ("demo_lan", 6), False, "blocked"),
        ("demo_tuan", "Free items nearby", ("demo_duc", 9), False, "blocked"),
        ("demo_minh", "Camera gear to browse", ("demo_huy", 0), True, "blocked"),
        ("demo_lan", "Books for a quiet evening", ("demo_mai", 0), False, "blocked"),
        ("demo_huy", "Second-hand phones", ("demo_minh", 0), False, "blocked"),
        ("demo_duc", "Camera gear for trips", ("demo_huy", 0), False, "blocked"),
        ("demo_mai", "Baby supplies to browse", ("demo_linh", 0), True, "blocked"),
        ("demo_linh", "Reading for the family", ("demo_mai", 1), False, "blocked"),
    )
    for index, (username, name, target, read, email_status) in enumerate(notifications):
        listing = listings[target]
        published_version = listing.published["version"]
        search = searches[(username, name)]
        notification, created = Notification.objects.get_or_create(
            user=users[username],
            search=search,
            listing=listing,
            listing_version=published_version,
            defaults={
                "read_at": now - timedelta(hours=1) if read else None,
                "email_status": email_status,
            },
        )
        if created:
            Notification.objects.filter(pk=notification.pk).update(
                created_at=listing.published_at + timedelta(minutes=10)
            )
    for (username, index), listing in listings.items():
        if not listing.published:
            continue
        anchor = (
            now
            if listing.status in ("active", "pending", "rejected")
            and listing.shop.status == "active"
            and not listing.moderation_hold
            and listing.retention_due_at > now
            else listing.published_at
        )
        for days_ago in range(3):
            for kind, count in (
                ("view", 8 + index * 3 + days_ago),
                ("call", 1 + index % 3),
                ("copy", index % 2),
            ):
                if kind != "view" and (
                    not listing.phone_consent or not users[username].privacy.share_phone
                ):
                    continue
                ListingMetric.objects.get_or_create(
                    listing=listing,
                    day=(anchor - timedelta(days=days_ago)).date(),
                    kind=kind,
                    defaults={"count": count},
                )
    seed_demo_reports(users, listings)


@transaction.atomic
def seed_demo_reports(users, listings):
    if not settings.DEMO_MODE:
        raise CommandError("Set DJANGO_DEMO_MODE=true before seeding demo data.")
    scenarios = (
        (
            "phone-condition",
            "demo_ha",
            ("demo_minh", 1),
            None,
            "incorrect",
            "open",
            "The frame marks need a clearer close-up. This is a fictional demo report.",
            None,
        ),
        (
            "camera-images",
            "demo_vy",
            ("demo_huy", 0),
            None,
            "images",
            "reviewing",
            "Please review the stock-image explanation. Demo evidence only.",
            "review",
        ),
        (
            "bag-hold",
            "demo_quang",
            ("demo_thao", 8),
            None,
            "incorrect",
            "resolved",
            "The bag condition needs clarification. Demo report.",
            "hide_listing",
        ),
        (
            "kitchen-shop",
            "demo_tuan",
            None,
            "demo_an",
            "fraud",
            "resolved",
            "A fictional demo concern led to a shop suspension.",
            "suspend_shop",
        ),
        (
            "bike-false-alarm",
            "demo_ha",
            ("demo_duc", 0),
            None,
            "spam",
            "dismissed",
            "The apparent duplicate was checked. Fictional demo report.",
            "dismiss",
        ),
        (
            "baby-age",
            "demo_quang",
            ("demo_linh", 2),
            None,
            "other",
            "open",
            "Please clarify the suitable age range. Demo concern only.",
            None,
        ),
        (
            "paused-pet",
            "demo_tuan",
            None,
            "demo_bao",
            "other",
            "reviewing",
            "Report filed while the shop was active, before it paused. Demo.",
            "review",
        ),
        (
            "books-policy",
            "demo_lan",
            ("demo_mai", 0),
            None,
            "prohibited",
            "dismissed",
            "Policy-category exercise only; the fictional item is an ordinary book.",
            "dismiss",
        ),
        (
            "shoes-fraud",
            "demo_vy",
            ("demo_duc", 2),
            None,
            "fraud",
            "open",
            "Please investigate the fictional condition discrepancy.",
            None,
        ),
    )
    for (
        key,
        username,
        target,
        shop_owner,
        reason,
        status,
        description,
        action,
    ) in scenarios:
        shop = users[shop_owner].shop if shop_owner else None
        report, created = Report.objects.get_or_create(
            id=uuid5(NAMESPACE_URL, f"chobe-demo-v1/report/{key}"),
            defaults={
                "reporter": users[username],
                "listing": listings[target] if target else None,
                "shop": shop,
                "reason": reason,
                "description": description,
                "status": status,
                "response": (
                    "We reviewed your demo report and recorded the outcome."
                    if status in ("resolved", "dismissed")
                    else ""
                ),
                "version": 2 if action else 1,
            },
        )
        if created and action:
            ReportDecision.objects.create(
                report=report,
                actor=users["demo_moderator"],
                action=action,
                reason=f"Demo internal review: {key}. Fictional evidence; no real accusation.",
            )


STORY_LABELS = {
    "active": "Đã duyệt, đang bán",
    "pending": "Tin mới chờ admin duyệt",
    "rejected": "Tin mới bị từ chối",
    "draft": "Nháp chưa đủ thông tin, chưa có ảnh",
    "hidden": "Chủ shop tự ẩn",
    "sold": "Chủ shop đánh dấu đã bán",
    "pending_edit": "Bản sửa chờ duyệt; bản cũ vẫn công khai",
    "rejected_edit": "Bản sửa bị từ chối; bản cũ vẫn công khai",
    "draft_edit": "Nháp sửa chưa gửi; bản cũ vẫn công khai",
    "report_hold": "Admin ẩn sau báo cáo; chủ shop không thể tự bật lại",
    "due_soon": "Sắp đến hạn 6 tháng; thử gia hạn",
    "expired": "Quá hạn, đã bị loại khỏi public trước khi cleanup",
    "retention_deleted": "Đã xóa nội dung/ảnh do retention",
    "owner_deleted": "Đã xóa nội dung/ảnh theo yêu cầu của chủ",
    "reapproved": "Admin duyệt → từ chối lại → khiếu nại → duyệt lại",
    "phone_hidden": "Không đồng ý công khai phone ở riêng tin này",
    "phone_withdrawn": "Rút consent phone ở nháp; snapshot cũ không được làm lộ số",
    "negotiable": "Giá thỏa thuận, không nhập số tiền",
    "free": "Cho tặng miễn phí",
    "retired_category": "Đã duyệt trước khi danh mục bị retire; hiện không public",
}
ROLE_LABELS = {
    "seller": "Chủ shop",
    "buyer": "Chỉ xem hàng, không có shop",
    "moderator": "Nhân viên duyệt tin + báo cáo + khóa shop",
    "catalog": "Nhân viên danh mục, không có quyền duyệt tin",
    "reports": "Nhân viên báo cáo, không có quyền ẩn tin/khóa shop",
    "inactive": "Tài khoản đã vô hiệu hóa trong kịch bản xóa",
}


def line(value):
    return str(value).replace("|", "/").replace("\n", " ")


def write_demo_guide(path, users, shops, listings, categories):
    visible = set(
        public_listings()
        .filter(pk__in=[item.pk for item in listings.values()])
        .values_list("pk", flat=True)
    )
    title_by_id = {
        item.pk: item.title or DEMO_PRODUCTS[username][index][0]
        for (username, index), item in listings.items()
    }
    category_names = {str(item.pk): item.name for item in categories.values()}
    rows = [
        "# Bộ dữ liệu demo Chobe",
        "",
        "> Đây là dữ liệu giả lập để review portfolio. Không có người bán, món hàng, cáo buộc, lượt xem hoặc giao dịch thật. Nội dung runtime dùng tiếng Anh và có nhãn Demo.",
        "",
        "## Đăng nhập nhanh",
        "",
        "- Trang đăng nhập: `http://localhost:4200/login` (đổi port nếu frontend của bạn dùng port khác).",
        f"- Mật khẩu chung của **tài khoản demo mới tạo**: `{DEMO_PASSWORD}`. Nếu bạn tự đổi mật khẩu sau đó, seed không đổi lại.",
        "- Các email dùng miền `demo.chobe.invalid`; phone dùng dải số hư cấu `+1 202 555 01xx`, không phải số người bán Việt Nam thật.",
        "- Tài khoản `admin` và các tài khoản có sẵn trước seed không bị đổi thông tin đăng nhập.",
        "- Không gọi AI, SMTP/SMS, không enqueue outbox, không bật worker. Export/deletion ở trạng thái chờ là snapshot mô phỏng, không phải tác vụ đang chạy thật.",
        "",
        "## Tổng quan",
        "",
        f"- {len(users)} tài khoản demo: 10 chủ shop, 5 người chỉ xem hàng, 3 staff có quyền khác nhau và 3 tài khoản vô hiệu hóa cho kịch bản xóa.",
        f"- {len(shops)} shop: "
        + ", ".join(
            f"{key}={value}"
            for key, value in sorted(
                Counter(shop.status for shop in shops.values()).items()
            )
        )
        + ".",
        f"- {len(listings)} kịch bản tin; hiện {len(visible)} tin đủ điều kiện công khai.",
        "- 8 danh mục gốc có sẵn được giữ lại; bổ sung nhánh demo và danh mục draft/restricted/retired.",
        "- Ảnh hàng là stock/ảnh minh họa được tái sử dụng từ prototype, không chứng minh mẫu hàng thật. Avatar/logo là hình minh họa; tên hiển thị và banner có nhãn Demo.",
        "- Lượt view/call/copy là số đếm giả lập. Các dòng favorite/follow trên nội dung nay không còn public mô phỏng việc người dùng đã lưu/theo dõi trước khi nội dung bị ẩn.",
        "",
        "## Danh sách tài khoản",
        "",
        "| Username | Tên hiển thị | Vai trò | Shop / trạng thái |",
        "|---|---|---|---|",
    ]
    for username, name, area, role, _, _ in DEMO_PEOPLE:
        user = users[username]
        shop = shops.get(username)
        rows.append(
            f"| `{username}` | {line(user.profile.display_name)} | {ROLE_LABELS[role]} | {line(shop.name) + ' / ' + shop.status if shop else 'Không có shop'} |"
        )
    rows.extend(
        [
            "",
            "## Review nhanh theo kịch bản",
            "",
            "1. **Khám phá/tìm kiếm:** mở `/`, `/search`, thử `Pixel`, `sofa`, `bicycle`, `books`; dùng bộ lọc danh mục/giá/khu vực. Các tin khác nhau có đủ để xem phân trang.",
            "2. **So sánh:** ba tin đầu của `demo_minh` cùng danh mục Phones, mở `/compare?ids=1101,1102,1103`. Chọn thêm một tin Furniture để xem lỗi khác danh mục.",
            "3. **Bản công khai tách nháp:** đăng nhập `demo_minh`, mở tin `1109`; bản sửa chờ duyệt trong khi người mua vẫn thấy bản cũ. `demo_lan` / `1209` có bản sửa bị từ chối; `demo_huy` / `1309` có nháp sửa chưa gửi.",
            "4. **Duyệt thủ công:** đăng nhập `demo_moderator`, mở `/admin/moderation`; lọc pending/rejected và open appeals, approve/reject kèm lý do. Tin `1110` đã có lịch sử admin đảo quyết định.",
            "5. **Báo cáo:** `demo_quang` đã báo cáo tin `1409`, admin ẩn tin và đặt hold. `demo_thao` không thể tự Show tin này. Cần sửa/gửi lại rồi admin duyệt.",
            "6. **Quyền staff:** `demo_reports` xem/xử lý báo cáo nhưng không có quyền hide listing hoặc suspend shop; `demo_catalog` chỉ quản lý danh mục. Dùng `/admin/reports`, `/admin/categories`, `/admin/moderation` để đối chiếu 403.",
            "7. **Shop không public:** `demo_bao` paused, `demo_an` suspended, `demo_nam` closed. Chủ vẫn đăng nhập và xem dữ liệu riêng; người mua không thấy storefront/tin công khai.",
            "8. **Privacy:** `demo_vy` không ghi lịch sử, không nhận alert. `demo_huy` và `demo_mai` đã rút consent phone toàn tài khoản. Tin `1210` tắt phone riêng; tin `1310` mô phỏng rút consent ở nháp.",
            "9. **Retention:** `demo_duc` / `1509` sắp đến hạn, có thể Renew; `demo_mai` / `1609` đã quá hạn và không public, `1610` đã bị xóa nội dung; `demo_linh` / `1710` đã xóa bởi chủ.",
            "10. **Inbox/saved search:** `demo_ha` có email opt-in nhưng seed không gửi thư; `demo_quang` chỉ inbox, gồm thông báo về tin nay đã ẩn; `demo_tuan` có một tìm kiếm paused.",
            "11. **Empty state:** `demo_trang` chưa có hoạt động marketplace: không shop, không follow/favorite/history/saved search/notification.",
            "12. **Export/xóa tài khoản:** xem trạng thái riêng ở `/account/privacy`; các receipt xóa và account inactive nằm ở phần cuối tài liệu. Không tạo session/token đăng nhập giả.",
            "",
            "## Chi tiết từng tài khoản",
            "",
            "Kịch bản là trạng thái seed ban đầu. Nếu bạn đã tự thay đổi dữ liệu khi review, cột trạng thái/public và thông tin tài khoản bên dưới lấy từ DB hiện hành; kịch bản ban đầu có thể đã thay đổi.",
            "",
        ]
    )
    for username, name, area, role, _, _ in DEMO_PEOPLE:
        user = users[username]
        profile, privacy = user.profile, user.privacy
        rows.extend(
            [
                f"### {username} — {profile.display_name}",
                "",
                f"- Đăng nhập: `{username}` / mật khẩu chung ở đầu tài liệu. "
                + (
                    "**Không đăng nhập được: account inactive.**"
                    if not user.is_active
                    else "Account đang active."
                ),
                f"- Email giả: `{user.email}`; khu vực: {profile.area}.",
                f"- Bio: {profile.bio}",
                "- Avatar: "
                + ("có hình minh họa" if profile.avatar else "chưa có")
                + f"; phone lưu trong profile: `{profile.phone or 'chưa nhập'}`.",
                f"- Privacy: chia sẻ phone **{'bật' if privacy.share_phone else 'tắt'}**; ghi lịch sử **{'bật' if privacy.record_history else 'tắt'}**.",
                f"- Vai trò: {ROLE_LABELS[role]}.",
                f"- Profile version `{profile.version}`; privacy version `{privacy.version}`.",
            ]
        )
        following = list(
            ShopFollow.objects.filter(user=user)
            .select_related("shop")
            .order_by("shop__slug")
        )
        rows.append(
            "- Đang theo dõi shop: "
            + (
                ", ".join(
                    f"{relation.shop.name} ({relation.shop.status})"
                    for relation in following
                )
                or "không có"
            )
            + "."
        )
        favorites = list(
            Favorite.objects.filter(user=user).values_list("listing_id", flat=True)
        )
        favorite_descriptions = []
        for pk in favorites:
            title = line(title_by_id.get(pk, "Tin ngoài bộ demo"))
            availability = (
                "đang public"
                if pk in visible
                else "không còn public, bị ẩn khỏi danh sách người mua"
            )
            favorite_descriptions.append(f"`{pk}` {title} [{availability}]")
        rows.append(
            "- Tin đã lưu: " + (", ".join(favorite_descriptions) or "không có") + "."
        )
        history = list(
            ViewingHistory.objects.filter(user=user).values_list(
                "listing_id", flat=True
            )
        )
        rows.append(
            "- Lịch sử đã ghi: "
            + (", ".join(f"`{pk}`" for pk in history) or "không có")
            + "."
        )
        preference = user.notificationpreference
        rows.append(
            f"- Thông báo: inbox **{'bật' if preference.inbox else 'tắt'}**, email **{'bật' if preference.email else 'tắt'}**; không có email nào được seed gửi ra."
        )
        if username in shops:
            shop = shops[username]
            rows.extend(
                [
                    f"- Shop: **{shop.name}**, trạng thái `{shop.status}`, khu vực {shop.area}.",
                    f"- Đường dẫn: `/shops/{shop.slug}`; giờ liên hệ {shop.contact_hours}. Có logo và banner minh họa.",
                    "- Địa chỉ cũ: "
                    + ", ".join(
                        f"`/shops/{slug}`"
                        for slug in shop.slugs.exclude(slug=shop.slug).values_list(
                            "slug", flat=True
                        )
                    )
                    + " (redirect khi shop đủ điều kiện public).",
                    "",
                    "| ID | Tin / danh mục | Trạng thái | Kịch bản | Public? |",
                    "|---|---|---|---|---|",
                ]
            )
            for index, product in enumerate(DEMO_PRODUCTS[username]):
                item = listings[(username, index)]
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
                price = (
                    "Thỏa thuận, chưa nhập giá"
                    if item.price is None
                    else f"{item.price:,} VND"
                )
                rows.append(
                    f"| `{item.pk}` | {line(item.title or 'Đã xóa: ' + product[0])}<br>{line(item.category.name if item.category_id else 'Nội dung/danh mục đã xóa')}<br>{price} | `{item.status}` | {STORY_LABELS[story]} | {'Có' if item.pk in visible else 'Không'} |"
                )
            rows.append("")
        else:
            rows.append("- Không có shop, không có tin bán.")
        searches = list(SavedSearch.objects.filter(user=user))
        if searches:
            rows.extend(["", "**Tìm kiếm đã lưu:**", ""])
            for search in searches:
                filters = {
                    key: category_names.get(value, value)
                    if key == "category"
                    else value
                    for key, value in search.filters.items()
                }
                rows.append(
                    f"- {search.name}: {line(filters)}; {'mỗi ngày' if search.frequency == 'daily' else 'khi có tin mới'}; {'đang bật' if search.active else 'tạm dừng'}."
                )
        for notification in Notification.objects.filter(user=user).select_related(
            "listing", "search"
        ):
            rows.append(
                f"- Inbox `{notification.pk}`: {notification.search.name} → tin `{notification.listing_id}`, {'đã đọc' if notification.read_at else 'chưa đọc'}, {'còn public' if notification.listing_id in visible else 'không còn public'}; email `{notification.email_status}` (trạng thái giả lập, không gửi thư)."
            )
        for report in Report.objects.filter(reporter=user):
            rows.append(
                f"- Báo cáo `{report.pk}`: {report.reason}, `{report.status}`, đối tượng "
                + (
                    f"tin `{report.listing_id}`"
                    if report.listing_id
                    else f"shop `{report.shop.slug}`"
                )
                + "."
            )
        for export in AccountDataExport.objects.filter(user=user):
            rows.append(
                f"- Export `{export.pk}`: `{export.status}`"
                + (
                    " — tải được snapshot dữ liệu của chính tài khoản này trong thời hạn."
                    if export.status == "ready"
                    else " — trạng thái mô phỏng, không có job nền tự chạy."
                )
            )
        if user.is_staff:
            rows.append(
                "- Quyền Django: "
                + ", ".join(
                    f"`{permission}`"
                    for permission in sorted(user.get_all_permissions())
                )
                + "."
            )
        rows.append("")
    rows.extend(
        [
            "## Danh mục và mô hình dữ liệu",
            "",
            "| Danh mục | Trạng thái | Nháp / public version |",
            "|---|---|---|",
        ]
    )
    for category in categories.values():
        rows.append(
            f"| {line(category.name)} (`{category.slug}`) | `{category.status}`"
            + (" / restricted" if category.restricted else "")
            + f" | {category.version} / {category.published.get('version', 'chưa publish')} |"
        )
    rows.extend(
        [
            "",
            "**Các model nghiệp vụ có dữ liệu:**",
            "",
            "- Accounts: User, Profile, PrivacySettings, ConsentEvent, ViewingHistory, AccountDataExport (đủ 5 trạng thái), DeletionRequest (đủ 4 trạng thái).",
            "- Shops: Shop (đủ 4 trạng thái), ShopSlug (địa chỉ cũ/mới), ShopAuditEvent, ShopFollow.",
            "- Categories: Category, CategoryRevision, CategoryAuditEvent; có nháp chưa publish, restricted, retired và public snapshot khác nháp.",
            "- Listings: Listing (đủ 7 trạng thái), ListingImage, ListingRevision, ModerationCase, ListingAuditEvent, Favorite, SavedSearch, NotificationPreference, Notification, Report, ReportDecision, ListingMetric.",
            "- Notification có đủ blocked/queued/sending/sent/failed dưới dạng trạng thái **mô phỏng**; kể cả sent cũng không phải bằng chứng gửi thư thật. Không có outbox chạy các dòng queued/sending này.",
            "- Không tạo session, access token, mật khẩu reset, kết quả AI giả, hoặc job outbox có thể gửi thông tin ra ngoài. Bảng hạ tầng không phải dữ liệu demo nghiệp vụ.",
            "",
            "## Receipt xóa tài khoản",
            "",
            "| Receipt | Account | Trạng thái |",
            "|---|---|---|",
        ]
    )
    for receipt in DeletionRequest.objects.filter(
        pk__in=[
            uuid5(NAMESPACE_URL, f"chobe-demo-v1/deletion/{status}")
            for status in ("requested", "processing", "failed", "completed")
        ]
    ).select_related("user"):
        rows.append(
            f"| `{receipt.pk}` | {receipt.user.username if receipt.user else 'Account đã xóa; receipt không giữ user'} | `{receipt.status}` |"
        )
    rows.extend(
        [
            "",
            "## Chạy lại seed",
            "",
            "Chạy các command Django theo thứ tự: `seed_demo_accounts`, `seed_demo_categories`, `seed_demo_shops`, `seed_demo_listings` với `DJANGO_DEMO_MODE=true`. Xem `backend/README.md` để biết tham số và thứ tự clear.",
            "",
            "- Mỗi command có transaction riêng, không backup tự động. Các lệnh `clear_seed_demo_<app>` chỉ dọn dữ liệu demo; chạy theo thứ tự listings → shops → categories → accounts.",
            "- Chạy lại không nhân đôi dữ liệu và không reset mật khẩu/profile/tin đã chỉnh khi review; tài liệu này được render lại từ DB hiện hành.",
            "- Các quan hệ follow/favorite/history hoặc dữ liệu demo đã xóa có thể được bổ sung lại khi chạy seed; các bản ghi còn tồn tại không bị cập nhật đè. Đây là seed bổ sung, không phải chức năng reset về nguyên trạng.",
            "- Nếu đổi tên/xóa tay một phần dữ liệu demo, seed không có chức năng reset phá hủy. Xung đột namespace với dữ liệu không thuộc demo sẽ dừng và rollback phần seed đang chạy.",
            "- Nếu chạy worker thật sau đó, các dữ liệu đã quá hạn có thể được cleanup theo policy. Đó là hành vi hệ thống thật; bộ seed không tự giữ tin quá hạn ở public.",
            "",
            "## Số liệu snapshot",
            "",
            "- Trạng thái tin: "
            + ", ".join(
                f"{key}={value}"
                for key, value in sorted(
                    Counter(item.status for item in listings.values()).items()
                )
            )
            + ".",
            f"- Tin có thể xem công khai lúc ghi tài liệu: {len(visible)}.",
            "- Dữ liệu và timestamp là kịch bản giả lập; không phải lịch sử giao dịch hoặc bằng chứng hoạt động thật.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8")


class Command(BaseCommand):
    help = "Seed demo listings, moderation, engagement and the review guide."

    def add_arguments(self, parser):
        parser.add_argument(
            "--guide",
            type=Path,
            default=settings.BASE_DIR.parent / "docs" / "DEMO_DATA.md",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError("Set DJANGO_DEMO_MODE=true before seeding demo data.")
        users = demo_accounts()
        shops = demo_shops(users)
        categories = demo_categories()
        retired_category = categories["retired-category"]
        retire_after_seed = not Listing.objects.filter(
            category=retired_category
        ).exists()
        listings = seed_demo_listings(users, shops, categories)
        seed_demo_engagement(users, listings, categories)
        if retire_after_seed and retired_category.status == "active":
            categories["retired-category"] = retire_category(
                users["demo_catalog"], retired_category, retired_category.version
            )
        write_demo_guide(options["guide"].resolve(), users, shops, listings, categories)
        self.stdout.write(self.style.SUCCESS(f"Demo listings ready: {len(listings)}."))
