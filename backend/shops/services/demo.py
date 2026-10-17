from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from django.core.management.base import CommandError
from django.utils import timezone

from accounts.services.demo import demo_image
from shops.models import Shop, ShopAuditEvent, ShopFollow, ShopSlug

DEMO_SHOPS = (
    (
        "demo_minh",
        "Minh Tech Corner",
        "minh-tech",
        "active",
        "Phones, audio and keyboards for a home desk.",
    ),
    (
        "demo_lan",
        "Lan Home Studio",
        "lan-home",
        "active",
        "Useful furniture and warm lighting for smaller homes.",
    ),
    (
        "demo_huy",
        "Huy Camera Shelf",
        "huy-camera",
        "active",
        "Second-hand camera gear with condition notes.",
    ),
    (
        "demo_thao",
        "Thao Second Look",
        "thao-style",
        "active",
        "Clothing and bags ready for another owner.",
    ),
    (
        "demo_duc",
        "Duc Outdoor Garage",
        "duc-outdoor",
        "active",
        "Bikes and sports items for weekend adventures.",
    ),
    (
        "demo_mai",
        "Mai Book Nook",
        "mai-books",
        "active",
        "Fiction, study books and affordable reading sets.",
    ),
    (
        "demo_linh",
        "Linh Little Steps",
        "linh-baby",
        "active",
        "Baby items with clear age and condition information.",
    ),
    (
        "demo_bao",
        "Bao Pet Supplies",
        "bao-pet",
        "paused",
        "Pet accessories only. This shop is taking a short break.",
    ),
    (
        "demo_an",
        "An Kitchen Finds",
        "an-kitchen",
        "suspended",
        "Kitchen appliances. A report led to a temporary suspension.",
    ),
    (
        "demo_nam",
        "Nam Moving Sale",
        "nam-moving",
        "closed",
        "A completed moving sale; this shop is now closed.",
    ),
)
DEMO_FOLLOWS = {
    "demo_minh": ("demo_lan", "demo_huy", "demo_duc"),
    "demo_lan": ("demo_minh", "demo_mai", "demo_linh"),
    "demo_huy": ("demo_minh", "demo_duc"),
    "demo_thao": ("demo_lan", "demo_mai"),
    "demo_duc": ("demo_huy", "demo_bao"),
    "demo_mai": ("demo_lan", "demo_linh"),
    "demo_linh": ("demo_mai", "demo_bao"),
    "demo_bao": ("demo_duc", "demo_linh"),
    "demo_an": ("demo_minh", "demo_nam"),
    "demo_nam": ("demo_lan", "demo_an"),
    "demo_ha": ("demo_minh", "demo_mai", "demo_duc"),
    "demo_quang": ("demo_lan", "demo_minh", "demo_duc"),
    "demo_vy": ("demo_huy", "demo_linh"),
    "demo_tuan": ("demo_thao", "demo_bao", "demo_an"),
    "demo_trang": (),
}


def seed_demo_shops(users):
    shops = {}
    for index, (username, name, slug, status, about) in enumerate(DEMO_SHOPS):
        key = uuid5(NAMESPACE_URL, f"chobe-demo-v1/shop/{username}")
        shop = Shop.objects.filter(owner=users[username]).first()
        if shop and shop.pk != key:
            raise CommandError(
                f"{username} already owns a shop outside this demo dataset."
            )
        if shop is None:
            if Shop.objects.filter(slug=f"demo-{slug}").exists():
                raise CommandError(
                    f"The reserved shop slug demo-{slug} is already in use."
                )
            shop = Shop.objects.create(
                id=key,
                owner=users[username],
                name=f"{name} (Demo)",
                slug=f"demo-{slug}",
                description=f"Demo seed v1. {about} All items and people are fictional.",
                area=users[username].profile.area,
                contact_hours="09:00–19:00, local time",
                website_url=f"https://{slug}.example.invalid",
                logo=demo_image("".join(part[0] for part in name.split()[:2])),
                banner=demo_image(f"{name} | DEMO", size=(1200, 360)),
                status=status,
                suspended_from="active" if status == "suspended" else "",
                version=3 if status != "active" else 2,
            )
            Shop.objects.filter(pk=key).update(
                created_at=timezone.now() - timedelta(days=300 + index * 5)
            )
            for address in (shop.slug, f"demo-{slug}-old"):
                ShopSlug.objects.create(shop=shop, slug=address)
            ShopAuditEvent.objects.create(
                shop=shop,
                actor=users[username],
                action="created",
                changes={"demo": True, "slug": f"demo-{slug}-old"},
            )
            ShopAuditEvent.objects.create(
                shop=shop,
                actor=users[username],
                action="updated",
                changes={"slug": {"from": f"demo-{slug}-old", "to": shop.slug}},
            )
            if status != "active":
                ShopAuditEvent.objects.create(
                    shop=shop,
                    actor=users["demo_moderator"]
                    if status == "suspended"
                    else users[username],
                    action="moderated" if status == "suspended" else "status_changed",
                    changes={"from": "active", "to": status, "demo": True},
                )
            events = list(shop.audit_events.order_by("pk"))
            for event_index, event in enumerate(events):
                ShopAuditEvent.objects.filter(pk=event.pk).update(
                    created_at=timezone.now()
                    - timedelta(
                        days=(
                            300 + index * 5
                            if event_index == 0
                            else 30
                            if event_index == 1
                            else 1
                        )
                    )
                )
        shops[username] = shop
    for username, following in DEMO_FOLLOWS.items():
        for index, owner in enumerate(following):
            relation, created = ShopFollow.objects.get_or_create(
                user=users[username], shop=shops[owner]
            )
            if created:
                ShopFollow.objects.filter(pk=relation.pk).update(
                    created_at=timezone.now() - timedelta(days=7, hours=index)
                )
    return shops
