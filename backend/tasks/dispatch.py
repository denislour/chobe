import os
from datetime import timedelta

from django.db import transaction
from django.tasks import TaskContext, TaskResultStatus
from django.tasks.signals import task_finished, task_started
from django.utils import timezone
from django_tasks_db.models import DBTaskResult, get_date_max
from huey import crontab
from huey.contrib.djhuey import HUEY, db_periodic_task, db_task, on_startup


def queue_outbox_task(task_id):
    job = DBTaskResult.objects.filter(
        pk=task_id,
        status=TaskResultStatus.READY,
        backend_name="default",
        queue_name="default",
    ).first()
    if job is None:
        return
    eta = None if job.run_after == get_date_max() else job.run_after
    HUEY.enqueue(execute_outbox_task.s(str(job.pk), eta=eta, priority=job.priority))


# Keep the serialized Huey identifiers readable for messages queued before the move.
@db_task(__module__="accounts.tasks.dispatch")
def execute_outbox_task(task_id):
    with transaction.atomic():
        job = (
            DBTaskResult.objects.ready()
            .filter(pk=task_id, backend_name="default", queue_name="default")
            .select_for_update(skip_locked=True)
            .first()
        )
        if job is None:
            return 0
        job.claim(f"huey-{os.getpid()}")

    backend_type = None
    try:
        task = job.task
        result = job.task_result
        backend_type = type(task.get_backend())
        task_started.send(sender=backend_type, task_result=result)
        args = result.args
        if task.takes_context:
            args = (TaskContext(task_result=result), *args)
        job.set_successful(task.call(*args, **result.kwargs))
    except Exception as error:
        job.set_failed(error)
        raise
    finally:
        if backend_type is not None:
            task_finished.send(sender=backend_type, task_result=job.task_result)
    return 1


@db_periodic_task(crontab(minute="*"), __module__="accounts.tasks.dispatch")
def dispatch_pending_tasks():
    task_ids = list(
        DBTaskResult.objects.ready()
        .filter(backend_name="default", queue_name="default")
        .values_list("pk", flat=True)[:100]
    )
    for task_id in task_ids:
        queue_outbox_task(str(task_id))
    return len(task_ids)


@on_startup()
def dispatch_on_startup():
    dispatch_pending_tasks()


@db_periodic_task(
    crontab(hour="3", minute="0"),
    retries=3,
    retry_delay=60,
    __module__="task_queue.tasks",
)
def cleanup_outbox_results():
    return (
        DBTaskResult.objects.finished()
        .filter(finished_at__lt=timezone.now() - timedelta(days=14))
        .delete()[0]
    )
