from django.db import migrations


TASK_PATHS = {
    "auth.tasks.send_welcome_email": "api.tasks.email.send_welcome_email",
    "auth.tasks.send_password_reset_email": "api.tasks.email.send_password_reset_email",
    "auth.tasks.send_password_changed_email": "api.tasks.email.send_password_changed_email",
    "accounts.privacy.tasks.build_account_data_export": "api.tasks.account_data.build_account_data_export",
    "accounts.privacy.tasks.delete_account_data": "api.tasks.account_data.delete_account_data",
}


def move_tasks(apps, schema_editor):
    tasks = apps.get_model("django_tasks_database", "DBTaskResult")
    for old, new in TASK_PATHS.items():
        tasks.objects.using(schema_editor.connection.alias).filter(
            task_path=old
        ).update(task_path=new)


def restore_tasks(apps, schema_editor):
    tasks = apps.get_model("django_tasks_database", "DBTaskResult")
    for old, new in TASK_PATHS.items():
        tasks.objects.using(schema_editor.connection.alias).filter(
            task_path=new
        ).update(task_path=old)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_merge_accounts_module")]

    operations = [migrations.RunPython(move_tasks, restore_tasks)]
