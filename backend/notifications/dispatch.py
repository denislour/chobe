from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from notifications.services import cleanup_notifications


@db_periodic_task(crontab(hour="3", minute="30"), retries=3, retry_delay=60)
def maintain_notifications():
    cleanup_notifications()
