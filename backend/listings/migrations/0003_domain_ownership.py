from django.db import migrations


MODEL_MOVES = (
    ("listings", "favorite", "engagement"),
    ("listings", "savedsearch", "engagement"),
    ("shops", "shopfollow", "engagement"),
    ("listings", "moderationcase", "moderation"),
    ("listings", "report", "moderation"),
    ("listings", "reportdecision", "moderation"),
    ("listings", "notification", "notifications"),
    ("listings", "notificationpreference", "notifications"),
)
TASK_PATHS = {
    "listings.tasks.notifications.match_listing_searches":
        "notifications.tasks.match_listing_searches",
    "listings.tasks.notifications.deliver_notification":
        "notifications.tasks.deliver_notification",
}


def move_metadata(apps, schema_editor, *, reverse=False):
    alias = schema_editor.connection.alias
    content_types = apps.get_model("contenttypes", "ContentType").objects.using(alias)
    for old, model, new in MODEL_MOVES:
        source, target = (new, old) if reverse else (old, new)
        content_type = content_types.filter(app_label=source, model=model).first()
        if content_type is None:
            continue
        if content_types.filter(app_label=target, model=model).exists():
            raise RuntimeError(
                f"Conflicting content type for {target}.{model}. "
                "Resolve duplicate metadata before migrating; permissions were not merged."
            )
        content_types.filter(pk=content_type.pk).update(app_label=target)
    tasks = apps.get_model("django_tasks_database", "DBTaskResult").objects.using(alias)
    for old, new in TASK_PATHS.items():
        source, target = (new, old) if reverse else (old, new)
        tasks.filter(task_path=source).update(task_path=target)


def forwards(apps, schema_editor):
    move_metadata(apps, schema_editor)


def backwards(apps, schema_editor):
    move_metadata(apps, schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0002_search_index"),
        ("engagement", "0001_initial"),
        ("moderation", "0001_initial"),
        ("notifications", "0001_initial"),
        ("shops", "0003_move_follow_to_engagement"),
        ("accounts", "0010_simplify_accounts"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="Notification"),
                migrations.DeleteModel(name="NotificationPreference"),
                migrations.DeleteModel(name="Favorite"),
                migrations.DeleteModel(name="SavedSearch"),
                migrations.DeleteModel(name="ReportDecision"),
                migrations.DeleteModel(name="Report"),
                migrations.DeleteModel(name="ModerationCase"),
            ],
        ),
        migrations.RunPython(forwards, backwards),
    ]
