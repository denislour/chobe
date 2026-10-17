from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from categories.management.commands.seed_demo_categories import (
    DEMO_CATEGORIES,
    DEMO_SUBCATEGORIES,
)
from categories.models import Category, CategoryAuditEvent, CategoryRevision
from listings.models import Listing


@transaction.atomic
def clear_seed_demo_categories():
    if not settings.DEMO_MODE:
        raise CommandError("Set DJANGO_DEMO_MODE=true before clearing demo data.")
    root_slugs = [slug for _, slug, _ in DEMO_CATEGORIES]
    child_slugs = [f"demo-{key}" for key, _, _ in DEMO_SUBCATEGORIES]
    child_slugs.extend(
        ["demo-draft-category", "demo-restricted-category", "demo-retired-category"]
    )
    categories = Category.objects.filter(
        Q(slug__in=root_slugs, description="Demo category for the Chobe portfolio.")
        | Q(slug__in=child_slugs, description__startswith="Demo seed v1:")
    )
    ids = set(categories.values_list("pk", flat=True))
    if Listing.objects.filter(category_id__in=ids).exists():
        raise CommandError(
            "Categories still have listings. Clear those listings first."
        )
    if Category.objects.filter(parent_id__in=ids).exclude(pk__in=ids).exists():
        raise CommandError(
            "Categories have children outside the demo. Nothing was cleared."
        )
    count = len(ids)
    CategoryRevision.objects.filter(category_id__in=ids).delete()
    CategoryAuditEvent.objects.filter(category_id__in=ids).delete()
    while ids:
        parents = set(
            Category.objects.filter(pk__in=ids).values_list("parent_id", flat=True)
        )
        leaves = ids - parents
        if not leaves:
            raise CommandError(
                "The category tree contains a cycle. Nothing was cleared."
            )
        Category.objects.filter(pk__in=leaves).delete()
        ids -= leaves
    return count


class Command(BaseCommand):
    help = (
        "Clear marked demo categories without removing shared or referenced taxonomy."
    )

    def handle(self, *args, **options):
        count = clear_seed_demo_categories()
        self.stdout.write(self.style.SUCCESS(f"Cleared {count} demo categories."))
