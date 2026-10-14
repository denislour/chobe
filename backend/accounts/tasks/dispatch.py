from django.core.management import call_command
from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from accounts.services.account_data import cleanup_account_data


@db_periodic_task(crontab(hour="3", minute="0"), retries=3, retry_delay=60)
def cleanup_account_data_and_sessions():
    cleanup_account_data()
    call_command("clearsessions", verbosity=0)
