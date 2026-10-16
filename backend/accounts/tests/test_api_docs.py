import json

from django.test import TestCase
from django.urls import resolve, reverse


class ApiDocsTests(TestCase):
    def test_schema_endpoint_returns_api_metadata(self):
        response = self.client.get("/api/v1/schema/", HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["info"]["title"], "Chobe API")

    def test_swagger_ui_is_available(self):
        response = self.client.get("/api/v1/docs/")

        self.assertEqual(response.status_code, 200)

    def test_action_responses_match_the_api_contract(self):
        response = self.client.get("/api/v1/schema/", HTTP_ACCEPT="application/json")
        paths = json.loads(response.content)["paths"]
        for path, method, statuses in [
            ("/api/v1/auth/login/", "post", ("200",)),
            ("/api/v1/auth/register/", "post", ("201",)),
            ("/api/v1/auth/session/", "get", ("200",)),
            ("/api/v1/auth/logout/", "post", ("204",)),
            ("/api/v1/profiles/me/", "get", ("200",)),
            ("/api/v1/profiles/me/", "patch", ("200",)),
            ("/api/v1/me/data-exports/", "get", ("200",)),
            ("/api/v1/me/data-exports/", "post", ("202",)),
            ("/api/v1/me/viewing-history/", "post", ("201", "204")),
            ("/api/v1/me/viewing-history/clear/", "delete", ("204",)),
            ("/api/v1/me/deletion-requests/", "post", ("202",)),
        ]:
            with self.subTest(path=path, method=method):
                self.assertEqual(set(paths[path][method]["responses"]), set(statuses))
        for path in (
            "/api/v1/auth/",
            "/api/v1/profiles/",
            "/api/v1/privacy-settings/",
            "/api/v1/shop-storefronts/",
        ):
            with self.subTest(path=path):
                self.assertNotIn(path, paths)
        self.assertNotIn("get", paths["/api/v1/shops/"])

    def test_resource_schema_preserves_arrays_binary_and_request_bodies(self):
        response = self.client.get("/api/v1/schema/", HTTP_ACCEPT="application/json")
        paths = json.loads(response.content)["paths"]
        for path in ("/api/v1/me/data-exports/", "/api/v1/me/viewing-history/"):
            with self.subTest(path=path):
                schema = paths[path]["get"]["responses"]["200"]["content"][
                    "application/json"
                ]["schema"]
                self.assertEqual(schema["type"], "array")
        avatar = paths["/api/v1/profiles/me/avatar/"]["get"]["responses"]["200"]
        self.assertEqual(avatar["content"]["image/jpeg"]["schema"]["format"], "binary")
        self.assertNotIn("requestBody", paths["/api/v1/me/data-exports/"]["post"])
        self.assertNotIn(
            "requestBody", paths["/api/v1/me/viewing-history/clear/"]["delete"]
        )
        self.assertIn("requestBody", paths["/api/v1/me/viewing-history/"]["post"])
        self.assertIn("requestBody", paths["/api/v1/profiles/me/"]["patch"])

    def test_urlconf_preserves_account_routes(self):
        for path, module in [
            ("/api/v1/auth/login/", "accounts.views.auth"),
            ("/api/v1/profiles/me/", "accounts.views.profile"),
            ("/api/v1/privacy-settings/me/", "accounts.views.privacy"),
            ("/api/v1/me/data-exports/", "accounts.views.privacy"),
            (
                "/api/v1/account-deletion-status/receipt/",
                "accounts.views.privacy",
            ),
        ]:
            with self.subTest(path=path):
                self.assertEqual(resolve(path).func.cls.__module__, module)
        self.assertEqual(reverse("auth-login"), "/api/v1/auth/login/")
        self.assertEqual(
            reverse(
                "data-export-download",
                kwargs={"pk": "00000000-0000-0000-0000-000000000001"},
            ),
            "/api/v1/me/data-exports/00000000-0000-0000-0000-000000000001/download/",
        )
