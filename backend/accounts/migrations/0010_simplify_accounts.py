from django.db import migrations


TASK_PATHS = {
    "modules.auth.tasks.send_welcome_email": "accounts.tasks.email.send_welcome_email",
    "modules.auth.tasks.send_password_reset_email": "accounts.tasks.email.send_password_reset_email",
    "modules.auth.tasks.send_password_changed_email": "accounts.tasks.email.send_password_changed_email",
    "modules.accounts.tasks.build_account_data_export": "accounts.tasks.account_data.build_account_data_export",
    "modules.accounts.tasks.delete_account_data": "accounts.tasks.account_data.delete_account_data",
}


def move_tasks(apps, schema_editor):
    tasks = apps.get_model("django_tasks_database", "DBTaskResult")
    for old, new in TASK_PATHS.items():
        tasks.objects.using(schema_editor.connection.alias).filter(task_path=old).update(
            task_path=new
        )


def restore_tasks(apps, schema_editor):
    tasks = apps.get_model("django_tasks_database", "DBTaskResult")
    for old, new in TASK_PATHS.items():
        tasks.objects.using(schema_editor.connection.alias).filter(task_path=new).update(
            task_path=old
        )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0009_modular_monolith")]

    operations = [migrations.RunPython(move_tasks, restore_tasks)]
