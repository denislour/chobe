from django.core.management.base import CommandError

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


def seed_demo_taxonomy(editor):
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


def finish_demo_taxonomy(editor, categories):
    category = categories["retired-category"]
    if category.status == "active" and getattr(category, "_demo_seed_created", False):
        categories["retired-category"] = retire_category(
            editor, category, category.version
        )
