from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from categories.models import Category
from categories.serializers.attributes import AttributeDefinitionSerializer
from categories.services.demo import DEMO_CATEGORIES
from categories.services.publication import publish_category, save_draft


class Command(BaseCommand):
    help = "Create an optional demo taxonomy without changing existing categories."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError(
                "Set DJANGO_DEMO_MODE=true before seeding demo categories."
            )
        user = User.objects.filter(
            username=options["username"],
            is_active=True,
            is_staff=True,
            is_superuser=True,
        ).first()
        if user is None:
            raise CommandError("Choose an existing active superuser.")
        created = 0
        with transaction.atomic():
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
        self.stdout.write(self.style.SUCCESS(f"Created {created} demo categories."))
