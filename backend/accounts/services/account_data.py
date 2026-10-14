from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from accounts.models import AccountDataExport, ViewingHistory
from accounts.serializers.account_data import AccountDataSnapshotSerializer
from accounts.services.privacy import privacy_for
from accounts.services.profile import profile_for


def build_account_data_export(job_id: str) -> int:
    try:
        with transaction.atomic():
            job = (
                AccountDataExport.objects.select_related("user")
                .filter(pk=job_id)
                .first()
            )
            if (
                job is None
                or job.status not in ("queued", "failed")
                or not job.user.is_active
            ):
                return 0
            job.status = AccountDataExport.Status.PROCESSING
            job.save(update_fields=("status",))
            user = job.user
            profile_for(user)
            privacy_for(user)
            job.payload = AccountDataSnapshotSerializer(user).data
            job.expires_at = timezone.now() + timedelta(hours=24)
            job.status = AccountDataExport.Status.READY
            job.save()
        return 1
    except Exception:
        AccountDataExport.objects.filter(pk=job_id).update(
            status=AccountDataExport.Status.FAILED, payload={}
        )
        raise


class ExportUnavailable(APIException):
    status_code = 409
    default_detail = "Your export is not ready yet."


class ExportExpired(APIException):
    status_code = 410
    default_detail = "This export has expired. Request a new one."


def request_account_data_export(user):
    from accounts.tasks.account_data import build_account_data_export

    with transaction.atomic():
        job = AccountDataExport.objects.filter(
            user=user, status__in=("queued", "processing")
        ).first()
        if job is None:
            job = AccountDataExport.objects.create(user=user)
            build_account_data_export.enqueue(str(job.pk))
    return job


def downloadable_account_data(job):
    if job.expires_at and job.expires_at <= timezone.now():
        AccountDataExport.objects.filter(pk=job.pk).update(status="expired", payload={})
        raise ExportExpired()
    if job.status != AccountDataExport.Status.READY:
        raise ExportUnavailable()
    return job.payload


def cleanup_account_data():
    now = timezone.now()
    history, _ = ViewingHistory.objects.filter(
        viewed_at__lt=now - timedelta(days=30)
    ).delete()
    exports = AccountDataExport.objects.filter(expires_at__lte=now).update(
        payload={}, status="expired"
    )
    return history, exports, 0
