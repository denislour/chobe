from functools import partial

from asgiref.sync import sync_to_async
from django.db import transaction
from django_tasks_db.backend import DatabaseBackend


class OutboxHueyBackend(DatabaseBackend):
    def enqueue(self, task, args, kwargs):
        from tasks.dispatch import queue_outbox_task

        result = super().enqueue(task, args, kwargs)
        transaction.on_commit(
            partial(queue_outbox_task, str(result.id)),
            using=result.db_result._state.db,
            robust=True,
        )
        return result

    async def aenqueue(self, task, args, kwargs):
        return await sync_to_async(self.enqueue, thread_sensitive=True)(
            task, args, kwargs
        )
