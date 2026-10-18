from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone
from django.utils.module_loading import import_string


class AccountTaskMigrationTests(TransactionTestCase):
    def test_simplification_preserves_jobs_forward_and_backward(self):
        before = [("accounts", "0009_modular_monolith")]
        after = [("accounts", "0010_simplify_accounts")]
        paths = (
            (
                "modules.auth.tasks.send_welcome_email",
                "accounts.tasks.email.send_welcome_email",
                1,
            ),
            (
                "modules.auth.tasks.send_password_reset_email",
                "accounts.tasks.email.send_password_reset_email",
                "member@example.com",
            ),
            (
                "modules.auth.tasks.send_password_changed_email",
                "accounts.tasks.email.send_password_changed_email",
                1,
            ),
            (
                "modules.accounts.tasks.build_account_data_export",
                "accounts.tasks.account_data.build_account_data_export",
                "export-id",
            ),
            (
                "modules.accounts.tasks.delete_account_data",
                "accounts.tasks.account_data.delete_account_data",
                "deletion-id",
            ),
        )
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            old_apps = executor.loader.project_state(before).apps
            tasks = old_apps.get_model("django_tasks_database", "DBTaskResult")
            records = []
            for old, new, argument in paths:
                record = tasks.objects.create(
                    task_path=old,
                    args_kwargs={"args": [argument], "kwargs": {}},
                    backend_name="default",
                    run_after=timezone.now(),
                )
                records.append((record.pk, old, new, record.args_kwargs, record.status))

            executor = MigrationExecutor(connection)
            executor.migrate(after)
            tasks = executor.loader.project_state(after).apps.get_model(
                "django_tasks_database", "DBTaskResult"
            )
            for pk, old, new, arguments, status in records:
                with self.subTest(path=old):
                    record = tasks.objects.get(pk=pk)
                    self.assertEqual(record.task_path, new)
                    self.assertEqual(record.args_kwargs, arguments)
                    self.assertEqual(record.status, status)
                    self.assertEqual(import_string(new).module_path, new)

            MigrationExecutor(connection).migrate(before)
            for pk, old, _, arguments, status in records:
                record = tasks.objects.get(pk=pk)
                self.assertEqual(record.task_path, old)
                self.assertEqual(record.args_kwargs, arguments)
                self.assertEqual(record.status, status)
        finally:
            MigrationExecutor(connection).migrate(latest)
