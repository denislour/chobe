from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from listings.services.management import cleanup_inactive_listings
from listings.services.notifications import cleanup_notifications, match_searches


@db_periodic_task(crontab(hour="3", minute="15"), retries=3, retry_delay=60)
def maintain_listings():
    cleanup_inactive_listings()
    cleanup_notifications()


@db_periodic_task(crontab(hour="4", minute="0"), retries=3, retry_delay=60)
def daily_saved_searches():
    match_searches(frequency="daily")
