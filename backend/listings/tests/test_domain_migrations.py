from datetime import timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class DomainOwnershipMigrationTests(TransactionTestCase):
    def test_move_and_rollback_preserve_data_permissions_jobs_and_search_index(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        old_targets = [
            ("engagement", None),
            ("moderation", None),
            ("notifications", None),
            ("shops", "0002_shopfollow"),
            ("listings", "0002_search_index"),
        ]
        try:
            executor.migrate(old_targets)
            old_apps = executor.loader.project_state(
                [
                    ("listings", "0002_search_index"),
                    ("accounts", "0010_simplify_accounts"),
                ]
            ).apps
            user = old_apps.get_model("accounts", "User").objects.create(
                username="migration-seller", is_staff=True
            )
            shop = old_apps.get_model("shops", "Shop").objects.create(
                owner=user, name="Migration shop", slug="migration-shop"
            )
            listing = old_apps.get_model("listings", "Listing").objects.create(
                shop=shop,
                last_owner_action_at=timezone.now(),
                retention_due_at=timezone.now() + timedelta(days=30),
                published={
                    "title": "migrationphone",
                    "description": "",
                    "area": "",
                    "attributes": {},
                },
            )
            revision = old_apps.get_model("listings", "ListingRevision").objects.create(
                listing=listing, version=1, snapshot={"title": "migrationphone"}
            )
            case = old_apps.get_model("listings", "ModerationCase").objects.create(
                revision=revision, appeal="Please review."
            )
            favorite = old_apps.get_model("listings", "Favorite").objects.create(
                user=user, listing=listing
            )
            follow = old_apps.get_model("shops", "ShopFollow").objects.create(
                user=user, shop=shop
            )
            search = old_apps.get_model("listings", "SavedSearch").objects.create(
                user=user, name="Phones", filters={"q": "phone"}
            )
            preference = old_apps.get_model(
                "listings", "NotificationPreference"
            ).objects.create(user=user, inbox=True)
            notification = old_apps.get_model(
                "listings", "Notification"
            ).objects.create(
                user=user, search=search, listing=listing, listing_version=1
            )
            report = old_apps.get_model("listings", "Report").objects.create(
                reporter=user, shop=shop, reason="spam", description="Please check."
            )
            decision = old_apps.get_model("listings", "ReportDecision").objects.create(
                report=report, actor=user, action="review", reason="Review started."
            )
            content_type, _ = old_apps.get_model(
                "contenttypes", "ContentType"
            ).objects.get_or_create(app_label="listings", model="report")
            permission, _ = old_apps.get_model(
                "auth", "Permission"
            ).objects.get_or_create(
                content_type=content_type,
                codename="review_report",
                defaults={"name": "Can review marketplace reports"},
            )
            group = old_apps.get_model("auth", "Group").objects.create(
                name="Report reviewers"
            )
            group.permissions.add(permission)
            user.groups.add(group)
            user.user_permissions.add(permission)
            task = old_apps.get_model(
                "django_tasks_database", "DBTaskResult"
            ).objects.create(
                task_path="listings.tasks.notifications.match_listing_searches",
                args_kwargs={"args": [listing.pk, 1], "kwargs": {}},
                backend_name="default",
                run_after=timezone.now(),
            )

            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            for app, model, pk in (
                ("engagement", "Favorite", favorite.pk),
                ("engagement", "ShopFollow", follow.pk),
                ("engagement", "SavedSearch", search.pk),
                ("moderation", "ModerationCase", case.pk),
                ("moderation", "Report", report.pk),
                ("moderation", "ReportDecision", decision.pk),
                ("notifications", "NotificationPreference", preference.pk),
                ("notifications", "Notification", notification.pk),
            ):
                with self.subTest(app=app, model=model):
                    self.assertTrue(
                        apps.get_model(app, model).objects.filter(pk=pk).exists()
                    )
            moved_notification = apps.get_model(
                "notifications", "Notification"
            ).objects.get(pk=notification.pk)
            self.assertEqual(moved_notification.search.filters, {"q": "phone"})
            self.assertEqual(moved_notification.listing_id, listing.pk)
            self.assertEqual(
                apps.get_model("moderation", "ModerationCase")
                .objects.get(pk=case.pk)
                .appeal,
                "Please review.",
            )
            from accounts.models import User

            current_user = User.objects.get(pk=user.pk)
            self.assertTrue(current_user.has_perm("moderation.review_report"))
            self.assertFalse(current_user.has_perm("listings.review_report"))
            self.assertTrue(
                current_user.user_permissions.filter(pk=permission.pk).exists()
            )
            self.assertTrue(
                current_user.groups.get(pk=group.pk)
                .permissions.filter(pk=permission.pk)
                .exists()
            )
            self.assertEqual(
                apps.get_model("contenttypes", "ContentType")
                .objects.get(pk=content_type.pk)
                .app_label,
                "moderation",
            )
            migrated_task = apps.get_model(
                "django_tasks_database", "DBTaskResult"
            ).objects.get(pk=task.pk)
            self.assertEqual(
                migrated_task.task_path, "notifications.tasks.match_listing_searches"
            )
            self.assertEqual(migrated_task.args_kwargs, task.args_kwargs)
            self.assertEqual(migrated_task.status, task.status)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT rowid FROM listings_search WHERE listings_search MATCH %s",
                    ["migrationphone"],
                )
                self.assertIn((listing.pk,), cursor.fetchall())

            MigrationExecutor(connection).migrate(old_targets)
            self.assertTrue(
                old_apps.get_model("listings", "Favorite")
                .objects.filter(pk=favorite.pk)
                .exists()
            )
            self.assertTrue(
                old_apps.get_model("shops", "ShopFollow")
                .objects.filter(pk=follow.pk)
                .exists()
            )
            self.assertEqual(
                old_apps.get_model("contenttypes", "ContentType")
                .objects.get(pk=content_type.pk)
                .app_label,
                "listings",
            )
            self.assertEqual(
                old_apps.get_model("django_tasks_database", "DBTaskResult")
                .objects.get(pk=task.pk)
                .task_path,
                task.task_path,
            )
        finally:
            MigrationExecutor(connection).migrate(latest)
