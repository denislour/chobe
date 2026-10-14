from django.core.management.base import BaseCommand

from accounts.services.account_data import cleanup_account_data


class Command(BaseCommand):
    help = "Remove expired account history, export content, and deletion receipts."

    def handle(self, *args, **options):
        history, exports, receipts = cleanup_account_data()
        self.stdout.write(
            f"Removed {history} history records and {receipts} receipts; expired {exports} exports."
        )
