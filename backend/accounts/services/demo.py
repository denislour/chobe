import io
from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from django.contrib.auth.models import Permission
from django.core.management.base import CommandError
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from accounts.models import (
    AccountDataExport,
    ConsentEvent,
    DeletionRequest,
    PrivacySettings,
    Profile,
    User,
)

DEMO_PASSWORD = "DemoChobe2026!"
DEMO_EMAIL_DOMAIN = "demo.chobe.invalid"
DEMO_PEOPLE = (
    ("demo_minh", "Minh Do", "Ho Chi Minh City", "seller", True, True),
    ("demo_lan", "Lan Nguyen", "Ha Noi", "seller", True, True),
    ("demo_huy", "Huy Tran", "Da Nang", "seller", False, True),
    ("demo_thao", "Thao Le", "Ho Chi Minh City", "seller", True, False),
    ("demo_duc", "Duc Pham", "Ha Noi", "seller", True, True),
    ("demo_mai", "Mai Vo", "Hue", "seller", False, True),
    ("demo_linh", "Linh Ho", "Da Nang", "seller", True, True),
    ("demo_bao", "Bao Dang", "Can Tho", "seller", True, True),
    ("demo_an", "An Bui", "Ho Chi Minh City", "seller", False, True),
    ("demo_nam", "Nam Vu", "Hai Phong", "seller", False, False),
    ("demo_ha", "Ha Nguyen", "Ha Noi", "buyer", False, True),
    ("demo_quang", "Quang Tran", "Ho Chi Minh City", "buyer", False, True),
    ("demo_vy", "Vy Le", "Da Nang", "buyer", False, False),
    ("demo_tuan", "Tuan Pham", "Can Tho", "buyer", False, True),
    ("demo_trang", "Trang Do", "Hue", "buyer", False, False),
    ("demo_moderator", "Demo Moderator", "Ha Noi", "moderator", False, False),
    ("demo_catalog", "Demo Catalog Editor", "Da Nang", "catalog", False, False),
    (
        "demo_reports",
        "Demo Report Reviewer",
        "Ho Chi Minh City",
        "reports",
        False,
        False,
    ),
    (
        "demo_delete_requested",
        "Demo Deletion Requested",
        "Ha Noi",
        "inactive",
        False,
        False,
    ),
    (
        "demo_delete_processing",
        "Demo Deletion Processing",
        "Da Nang",
        "inactive",
        False,
        False,
    ),
    ("demo_delete_failed", "Demo Deletion Failed", "Hue", "inactive", False, False),
)
ROLE_PERMISSIONS = {
    "moderator": (
        "listings.view_listing",
        "listings.moderate_listing",
        "listings.view_moderationcase",
        "listings.view_report",
        "listings.review_report",
        "shops.view_shop",
        "shops.change_shop",
    ),
    "catalog": (
        "categories.view_category",
        "categories.add_category",
        "categories.change_category",
        "categories.publish_category",
        "categories.retire_category",
        "categories.view_categoryrevision",
        "categories.view_categoryauditevent",
    ),
    "reports": ("listings.view_report", "listings.review_report"),
}


def demo_image(label, *, size=(256, 256), color="#ffd53d"):
    image = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=32 if size[0] < 600 else 44)
    draw.text(
        (size[0] // 2, size[1] // 2), label, font=font, fill="#24251f", anchor="mm"
    )
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85)
    return output.getvalue()


def seed_demo_accounts():
    users = {}
    now = timezone.now()
    for index, (username, name, area, role, share_phone, history) in enumerate(
        DEMO_PEOPLE
    ):
        email = f"{username}@{DEMO_EMAIL_DOMAIN}"
        user = User.objects.filter(username=username).first()
        if user and user.email != email:
            raise CommandError(
                f"The reserved demo username {username} belongs to another account."
            )
        if user is None:
            user = User(
                username=username,
                email=email,
                first_name=name.split()[0],
                last_name=name.split()[-1],
                is_active=role != "inactive",
                is_staff=role in ROLE_PERMISSIONS,
            )
            user.set_password(DEMO_PASSWORD)
            user.save()
            User.objects.filter(pk=user.pk).update(
                date_joined=now - timedelta(days=400 + index * 7),
                last_login=now - timedelta(hours=index + 1) if user.is_active else None,
            )
            Profile.objects.create(
                user=user,
                display_name=f"{name} (Demo)",
                area=area,
                bio=f"Demo account. {('Sharing useful second-hand items.' if role == 'seller' else 'Browsing the Chobe demo marketplace.')} No real person or transaction.",
                phone=f"+120255501{index:02d}" if role == "seller" else "",
                avatar=demo_image("".join(part[0] for part in name.split()[:2])),
                version=2,
            )
            PrivacySettings.objects.create(
                user=user,
                share_phone=share_phone,
                record_history=history,
                consent_at=now - timedelta(days=14),
                version=2,
            )
            ConsentEvent.objects.create(user=user, share_phone=share_phone)
            if username in ("demo_huy", "demo_mai"):
                ConsentEvent.objects.filter(user=user).update(
                    share_phone=True, created_at=now - timedelta(days=20)
                )
                ConsentEvent.objects.create(user=user, share_phone=False)
                PrivacySettings.objects.filter(user=user).update(version=3)
            for permission in ROLE_PERMISSIONS.get(role, ()):
                app_label, codename = permission.split(".")
                user.user_permissions.add(
                    Permission.objects.get(
                        content_type__app_label=app_label, codename=codename
                    )
                )
        users[username] = user
    return users


def seed_demo_account_lifecycle(users):
    now = timezone.now()
    exports = (
        ("demo_ha", "queued"),
        ("demo_quang", "processing"),
        ("demo_vy", "ready"),
        ("demo_tuan", "failed"),
        ("demo_trang", "expired"),
    )
    for username, status in exports:
        key = uuid5(NAMESPACE_URL, f"chobe-demo-v1/export/{username}")
        payload = {}
        if status == "ready":
            from accounts.serializers.account_data import AccountDataSnapshotSerializer

            payload = AccountDataSnapshotSerializer(users[username]).data
        export, created = AccountDataExport.objects.get_or_create(
            id=key,
            defaults={
                "user": users[username],
                "status": status,
                "payload": payload,
                "expires_at": now + timedelta(hours=23)
                if status == "ready"
                else now - timedelta(days=1)
                if status == "expired"
                else None,
            },
        )
        if created:
            ages = {
                "queued": timedelta(minutes=10),
                "processing": timedelta(minutes=5),
                "ready": timedelta(hours=1),
                "failed": timedelta(hours=3),
                "expired": timedelta(days=2),
            }
            AccountDataExport.objects.filter(pk=export.pk).update(
                created_at=now - ages[status]
            )
    for status in ("requested", "processing", "failed", "completed"):
        key = uuid5(NAMESPACE_URL, f"chobe-demo-v1/deletion/{status}")
        receipt, created = DeletionRequest.objects.get_or_create(
            id=key,
            defaults={
                "user": None
                if status == "completed"
                else users[f"demo_delete_{status}"],
                "status": status,
                "completed_at": now - timedelta(days=1)
                if status == "completed"
                else None,
            },
        )

        if created:
            DeletionRequest.objects.filter(pk=receipt.pk).update(
                created_at=now - timedelta(days=2)
                if status == "completed"
                else now - timedelta(hours=2)
            )
