from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from categories.models import Category
from categories.serializers.attributes import AttributeDefinitionSerializer
from categories.services.publication import (
    publish_category,
    retire_category,
    save_draft,
)

DEMO_CATEGORIES = (
    (
        "Electronics",
        "electronics",
        [
            {"key": "brand", "label": "Brand", "type": "text", "filterable": True},
            {
                "key": "storage_gb",
                "label": "Storage",
                "type": "integer",
                "unit": "GB",
                "min_value": 1,
                "filterable": True,
            },
        ],
    ),
    (
        "Home appliances",
        "home-appliances",
        [
            {
                "key": "power_w",
                "label": "Power",
                "type": "integer",
                "unit": "W",
                "min_value": 1,
            }
        ],
    ),
    (
        "Furniture",
        "furniture",
        [
            {
                "key": "material",
                "label": "Material",
                "type": "select",
                "filterable": True,
                "choices": [
                    {"value": "wood", "label": "Wood"},
                    {"value": "metal", "label": "Metal"},
                    {"value": "fabric", "label": "Fabric"},
                ],
            }
        ],
    ),
    (
        "Fashion",
        "fashion",
        [{"key": "size", "label": "Size", "type": "text", "filterable": True}],
    ),
    (
        "Sports",
        "sports",
        [{"key": "brand", "label": "Brand", "type": "text", "filterable": True}],
    ),
    (
        "Books",
        "books",
        [{"key": "language", "label": "Language", "type": "text", "filterable": True}],
    ),
    (
        "Baby supplies",
        "baby-supplies",
        [
            {
                "key": "age_months",
                "label": "Recommended age",
                "type": "integer",
                "unit": "months",
                "min_value": 0,
            }
        ],
    ),
    (
        "Pet supplies",
        "pet-supplies",
        [{"key": "material", "label": "Material", "type": "text"}],
    ),
)

DEMO_SUBCATEGORIES = (
    ("phones", "Phones", "electronics"),
    ("audio", "Audio", "electronics"),
    ("cameras", "Cameras", "electronics"),
    ("keyboards", "Keyboards", "electronics"),
    ("seating", "Seating", "furniture"),
    ("tables", "Tables", "furniture"),
    ("lighting", "Lighting", "furniture"),
    ("bags", "Bags", "fashion"),
    ("clothing", "Clothing", "fashion"),
    ("bicycles", "Bicycles", "sports"),
    ("sports-shoes", "Sports shoes", "sports"),
    ("fiction", "Fiction", "books"),
    ("study", "Study books", "books"),
    ("baby-gear", "Baby gear", "baby-supplies"),
    ("pet-accessories", "Pet accessories", "pet-supplies"),
    ("kitchen", "Kitchen appliances", "home-appliances"),
)


@transaction.atomic
def seed_demo_taxonomy(editor):
    if not settings.DEMO_MODE:
        raise CommandError("Set DJANGO_DEMO_MODE=true before seeding demo data.")
    categories = {}
    for index, (name, slug, fields) in enumerate(DEMO_CATEGORIES):
        category = Category.objects.filter(slug=slug).first()
        if category is None:
            serializer = AttributeDefinitionSerializer(data=fields, many=True)
            serializer.is_valid(raise_exception=True)
            category = save_draft(
                editor,
                {
                    "name": name,
                    "slug": slug,
                    "sort_order": index,
                    "description": "Demo category for the Chobe portfolio.",
                    "attributes": serializer.validated_data,
                },
            )
            category = publish_category(editor, category, category.version)
        if category.status != "active" or not category.published:
            raise CommandError(
                f"Publish the existing root category {slug} before seeding the marketplace demo."
            )
        categories[slug] = category
    scenarios = [
        (key, name, categories[parent]) for key, name, parent in DEMO_SUBCATEGORIES
    ]
    scenarios.extend(
        (key, name, categories["electronics"])
        for key, name in (
            ("draft-category", "Draft accessories"),
            ("restricted-category", "Restricted demo category"),
            ("retired-category", "Retired accessories"),
        )
    )
    for index, (key, name, parent) in enumerate(scenarios):
        slug = f"demo-{key}"
        category = Category.objects.filter(slug=slug).first()
        created = category is None
        if category and not category.description.startswith("Demo seed v1:"):
            raise CommandError(f"The reserved category {slug} is already in use.")
        if category is None:
            category = save_draft(
                editor,
                {
                    "name": f"{name} (Demo)",
                    "slug": slug,
                    "parent": parent,
                    "sort_order": index,
                    "description": f"Demo seed v1: {key}. Fictional taxonomy scenario.",
                    "attributes": parent.published["attributes"],
                    "restricted": key == "restricted-category",
                },
            )
            if key not in ("draft-category", "restricted-category"):
                category = publish_category(editor, category, category.version)
            if key == "phones":
                category = save_draft(
                    editor,
                    {
                        "version": category.version,
                        "description": f"Demo seed v1: {key}. Unpublished editorial changes; the public snapshot stays unchanged.",
                    },
                    category,
                )
        category._demo_seed_created = created
        categories[key] = category
    return categories


@transaction.atomic
def finish_demo_taxonomy(editor, categories):
    if not settings.DEMO_MODE:
        raise CommandError("Set DJANGO_DEMO_MODE=true before seeding demo data.")
    category = categories["retired-category"]
    if category.status == "active" and getattr(category, "_demo_seed_created", False):
        categories["retired-category"] = retire_category(
            editor, category, category.version
        )


@transaction.atomic
def seed_demo_categories(username):
    if not settings.DEMO_MODE:
        raise CommandError("Set DJANGO_DEMO_MODE=true before seeding demo categories.")
    user = User.objects.filter(
        username=username,
        is_active=True,
        is_staff=True,
        is_superuser=True,
    ).first()
    if user is None:
        raise CommandError("Choose an existing active superuser.")
    created = 0
    for index, (name, slug, fields) in enumerate(DEMO_CATEGORIES):
        if Category.objects.filter(slug=slug).exists():
            continue
        serializer = AttributeDefinitionSerializer(data=fields, many=True)
        serializer.is_valid(raise_exception=True)
        category = save_draft(
            user,
            {
                "name": name,
                "slug": slug,
                "sort_order": index,
                "description": "Demo category for the Chobe portfolio.",
                "attributes": serializer.validated_data,
            },
        )
        publish_category(user, category, category.version)
        created += 1
    return created


def demo_categories():
    slugs = {slug: slug for _, slug, _ in DEMO_CATEGORIES}
    slugs.update({key: f"demo-{key}" for key, _, _ in DEMO_SUBCATEGORIES})
    slugs.update(
        {
            key: f"demo-{key}"
            for key in ("draft-category", "restricted-category", "retired-category")
        }
    )
    existing = {
        item.slug: item for item in Category.objects.filter(slug__in=slugs.values())
    }
    if set(slugs.values()) - existing.keys():
        raise CommandError("Run seed_demo_categories before seeding demo listings.")
    root_slugs = {slug for _, slug, _ in DEMO_CATEGORIES}
    if any(
        slug not in root_slugs
        and not existing[slug].description.startswith("Demo seed v1:")
        for slug in slugs.values()
    ):
        raise CommandError("A reserved demo category belongs to another dataset.")
    return {key: existing[slug] for key, slug in slugs.items()}


class Command(BaseCommand):
    help = "Seed demo taxonomy and attribute scenarios."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo_catalog")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError("Set DJANGO_DEMO_MODE=true before seeding demo data.")
        editor = User.objects.filter(
            username=options["username"], is_active=True, is_staff=True
        ).first()
        if editor is None:
            raise CommandError("Choose an existing active staff taxonomy editor.")
        categories = seed_demo_taxonomy(editor)
        self.stdout.write(
            self.style.SUCCESS(f"Demo categories ready: {len(categories)}.")
        )
