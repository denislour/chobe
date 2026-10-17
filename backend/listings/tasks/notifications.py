from django.tasks import task

from listings.services.notifications import match_searches, send_notification_email


@task
def match_listing_searches(listing_id: int, version: int) -> int:
    return match_searches(listing_id, version)


@task
def deliver_notification(notification_id: int) -> bool:
    return send_notification_email(notification_id)
