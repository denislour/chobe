import ast
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import resolve


class MarketplaceBoundaryTests(SimpleTestCase):
    def test_existing_urls_resolve_to_the_owning_apps(self):
        for path, module in (
            ("listings/", "discovery.views"),
            ("home/", "discovery.views"),
            ("me/listings/", "listings.views.management"),
            ("me/favorites/", "engagement.views.favorites"),
            ("me/followed-shops/", "engagement.views.following"),
            ("me/saved-searches/", "engagement.views.searches"),
            ("me/notifications/", "notifications.views"),
            ("me/reports/", "moderation.views.reports"),
            ("admin/moderation/", "moderation.views.reviews"),
            ("admin/reports/", "moderation.views.reports"),
        ):
            with self.subTest(path=path):
                view = resolve(f"/api/v1/{path}").func.cls
                self.assertEqual(view.__module__, module)

    def test_listing_lifecycle_does_not_import_its_consumers(self):
        root = Path(settings.BASE_DIR) / "listings"
        files = [root / "models.py", root / "public.py", *root.glob("services/*.py")]
        forbidden = {
            "discovery",
            "engagement",
            "moderation",
            "notifications",
            "workflows",
        }
        for path in files:
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text())
                for node in ast.walk(tree):
                    modules = []
                    if isinstance(node, ast.ImportFrom) and node.module:
                        modules = [node.module]
                    elif isinstance(node, ast.Import):
                        modules = [alias.name for alias in node.names]
                    for module in modules:
                        self.assertNotIn(module.split(".")[0], forbidden)
