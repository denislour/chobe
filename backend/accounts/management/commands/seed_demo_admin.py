from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Create or update the demo admin account."

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(username="admin")
        user.is_active = user.is_staff = user.is_superuser = True
        if not user.check_password("abc123ABC!!!"):
            user.set_password("abc123ABC!!!")
        user.save()
        self.stdout.write(self.style.SUCCESS("Demo admin is ready."))
