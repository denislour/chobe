import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.cache import caches
from django.db import router
from django.test import SimpleTestCase

from accounts.models import User


class DatabaseCacheTests(SimpleTestCase):
    def test_router_keeps_cache_and_business_tables_separate(self):
        model = caches["default"].cache_model_class
        self.assertEqual(router.db_for_read(model), "cache")
        self.assertEqual(router.db_for_write(model), "cache")
        self.assertTrue(router.allow_migrate("cache", "django_cache"))
        self.assertFalse(router.allow_migrate("default", "django_cache"))
        self.assertFalse(router.allow_migrate("cache", "accounts"))
        self.assertEqual(router.db_for_write(User), "default")

    def test_file_cache_uses_wal_and_is_shared_between_processes(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "cache.sqlite3"
            environment = {
                **os.environ,
                "DJANGO_SETTINGS_MODULE": "config.settings",
                "DJANGO_CACHE_DB_PATH": str(path),
                "DJANGO_QUEUE_DB_PATH": str(Path(directory) / "queue.sqlite3"),
            }
            bootstrap = """
import django
django.setup()
from types import SimpleNamespace
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from accounts.throttles import (
    AccountDataExportThrottle, LoginAccountThrottle, LoginIPThrottle,
)
request = Request(
    APIRequestFactory().post(
        "/", {"username": "shared-member"}, format="json",
        REMOTE_ADDR="192.0.2.1",
    ),
    parsers=[JSONParser()],
)
request.user = SimpleNamespace(is_authenticated=True, pk=42)
throttle_types = (LoginIPThrottle, LoginAccountThrottle, AccountDataExportThrottle)
"""
            setup = (
                bootstrap
                + """
from django.core.cache import cache
from django.core.management import call_command
call_command("createcachetable", database="cache", verbosity=0)
cache.set("shared-key", "shared-value", timeout=60)
for throttle_type in throttle_types:
    for _ in range(throttle_type().num_requests):
        assert throttle_type().allow_request(request, None)
"""
            )
            subprocess.run(
                [sys.executable, "-c", setup],
                cwd=settings.BASE_DIR,
                env=environment,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            read = (
                bootstrap
                + """
import json
from django.core.cache import cache
from django.db import connections
with connections["cache"].cursor() as cursor:
    mode = cursor.execute("PRAGMA journal_mode").fetchone()[0]
print(json.dumps({
    "mode": mode,
    "value": cache.get("shared-key"),
    "tables": connections["cache"].introspection.table_names(),
    "throttles": {
        throttle_type.scope: throttle_type().allow_request(request, None)
        for throttle_type in throttle_types
    },
}))
"""
            )
            result = subprocess.run(
                [sys.executable, "-c", read],
                cwd=settings.BASE_DIR,
                env=environment,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            self.assertEqual(
                json.loads(result.stdout),
                {
                    "mode": "wal",
                    "value": "shared-value",
                    "tables": ["cache_entries"],
                    "throttles": {
                        "login_ip": False,
                        "login_account": False,
                        "data_export": False,
                    },
                },
            )
