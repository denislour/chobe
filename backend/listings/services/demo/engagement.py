from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from django.utils import timezone

from accounts.models import ViewingHistory
from listings.models import (
    Favorite,
    ListingMetric,
    Notification,
    NotificationPreference,
    Report,
    ReportDecision,
    SavedSearch,
)

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


def seed_demo_engagement(users, listings, categories):
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


def seed_demo_reports(users, listings):
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
