from django.db import migrations


TASK_PATHS = {
    "account.privacy.tasks.build_account_data_export": "accounts.privacy.tasks.build_account_data_export",
    "account.privacy.tasks.delete_account_data": "accounts.privacy.tasks.delete_account_data",
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
    dependencies = [("accounts", "0006_group_account_modules")]

    operations = [migrations.RunPython(move_tasks, restore_tasks)]
