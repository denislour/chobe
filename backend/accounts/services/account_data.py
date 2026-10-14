from datetime import timedelta

from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone
from django_tasks_db.models import DBTaskResult
from rest_framework.exceptions import APIException, ValidationError

from accounts.models import (
    AccountDataExport,
    DeletionRequest,
    User,
    ViewingHistory,
)
from accounts.serializers.account_data import AccountDataSnapshotSerializer
from accounts.services.privacy import privacy_for, withdraw_phone_consent
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


def delete_account_data(job_id: str) -> int:
    try:
        with transaction.atomic():
            job = (
                DeletionRequest.objects.select_related("user").filter(pk=job_id).first()
            )
            if job is None or job.status == DeletionRequest.Status.COMPLETED:
                return 0
            job.status = DeletionRequest.Status.PROCESSING
            job.save(update_fields=("status",))
            if job.user is not None:
                user = job.user
                for session in Session.objects.all().iterator():
                    if session.get_decoded().get("_auth_user_id") == str(user.pk):
                        session.delete()
                from accounts.tasks.email import (
                    send_password_changed_email,
                    send_password_reset_email,
                    send_welcome_email,
                )

                for email_task, argument, lookup in (
                    (send_welcome_email, user.pk, "args_kwargs__args__0"),
                    (send_password_changed_email, user.pk, "args_kwargs__args__0"),
                    (
                        send_password_reset_email,
                        user.email,
                        "args_kwargs__args__0__iexact",
                    ),
                ):
                    DBTaskResult.objects.filter(
                        task_path=email_task.module_path, **{lookup: argument}
                    ).delete()
                user.delete()
            job.user_id = None
            job.status = DeletionRequest.Status.COMPLETED
            job.completed_at = timezone.now()
            job.save()
        return 1
    except Exception:
        DeletionRequest.objects.filter(pk=job_id).update(
            status=DeletionRequest.Status.FAILED
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


def request_account_deletion(user):
    from accounts.tasks.account_data import delete_account_data

    with transaction.atomic():
        if not User.objects.filter(
            pk=user.pk, password=user.password, is_active=True
        ).update(is_active=False):
            raise ValidationError(
                "Your account has changed. Log in again before deleting it."
            )
        job = DeletionRequest.objects.create(user=user)
        withdraw_phone_consent(user)
        delete_account_data.enqueue(str(job.pk))
    return job


def cleanup_account_data():
    now = timezone.now()
    history, _ = ViewingHistory.objects.filter(
        viewed_at__lt=now - timedelta(days=30)
    ).delete()
    exports = AccountDataExport.objects.filter(expires_at__lte=now).update(
        payload={}, status="expired"
    )
    receipts, _ = DeletionRequest.objects.filter(
        status="completed", completed_at__lt=now - timedelta(days=7)
    ).delete()
    return history, exports, receipts
