from django.core.management.base import BaseCommand

from accounts.constants import DEMO_ADMIN_PASSWORD, DEMO_ADMIN_USERNAME
from accounts.models import User


class Command(BaseCommand):
    help = "Create or update the demo admin account."

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(username=DEMO_ADMIN_USERNAME)
        user.is_active = user.is_staff = user.is_superuser = True
        if not user.check_password(DEMO_ADMIN_PASSWORD):
            user.set_password(DEMO_ADMIN_PASSWORD)
        user.save()
        self.stdout.write(self.style.SUCCESS("Demo admin is ready."))
