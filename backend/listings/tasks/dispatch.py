from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from listings.services.management import cleanup_inactive_listings
from listings.services.notifications import cleanup_notifications


@db_periodic_task(crontab(hour="3", minute="15"), retries=3, retry_delay=60)
def maintain_listings():
    cleanup_inactive_listings()


