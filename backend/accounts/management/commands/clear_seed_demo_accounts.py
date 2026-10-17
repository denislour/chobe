from uuid import NAMESPACE_URL, uuid5

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from accounts.management.commands.seed_demo_accounts import demo_accounts
from accounts.models import DeletionRequest, User
from shops.models import Shop


@transaction.atomic
def clear_seed_demo_accounts():
    if not settings.DEMO_MODE:
        raise CommandError("Set DJANGO_DEMO_MODE=true before clearing demo data.")
    users = list(demo_accounts(require_all=False).values())
    if Shop.objects.filter(owner__in=users).exists():
        raise CommandError("Clear demo shops first. Accounts with shops are preserved.")
    receipt_ids = [
        uuid5(NAMESPACE_URL, f"chobe-demo-v1/deletion/{status}")
        for status in ("requested", "processing", "failed", "completed")
    ]
    DeletionRequest.objects.filter(pk__in=receipt_ids).filter(
        Q(user__in=users) | Q(user__isnull=True, status="completed")
    ).delete()
    queryset = User.objects.filter(pk__in=[user.pk for user in users])
    count = queryset.count()
    queryset.delete()
    return count


class Command(BaseCommand):
    help = "Clear reserved demo accounts and their account data; preserve the admin."

    def handle(self, *args, **options):
        count = clear_seed_demo_accounts()
        self.stdout.write(self.style.SUCCESS(f"Cleared {count} demo accounts."))
