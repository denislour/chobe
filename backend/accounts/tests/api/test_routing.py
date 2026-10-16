from accounts.models import AccountDataExport
from accounts.tests.base import AccountAPITestCase


class AccountRoutingTests(AccountAPITestCase):
    def test_auth_actions_work_without_exposing_inherited_crud(self):
        self.assertEqual(self.request("get", "auth").status_code, 405)
        self.assertEqual(self.request("post", "auth", {}).status_code, 405)
        self.assertEqual(self.request("get", f"auth/{self.user.pk}").status_code, 405)
        session = self.request("get", "auth/session")
        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.data["user"]["id"], self.user.pk)
        self.assertEqual(self.request("post", "auth/logout", {}).status_code, 204)

    def test_export_inherited_writes_remain_unavailable(self):
        job = AccountDataExport.objects.create(user=self.user)
        path = f"me/data-exports/{job.pk}"
        self.assertEqual(self.request("get", path).status_code, 200)
        for method in ("put", "patch", "delete"):
            with self.subTest(method=method):
                self.assertEqual(self.request(method, path, {}).status_code, 405)
        self.assertTrue(AccountDataExport.objects.filter(pk=job.pk).exists())

    def test_singletons_return_objects_and_do_not_expose_extra_crud_methods(self):
        for path in ("profiles/me", "privacy-settings/me"):
            with self.subTest(path=path):
                response = self.request("get", path)
                self.assertEqual(response.status_code, 200)
                self.assertIsInstance(response.data, dict)
                for method in ("post", "put", "delete"):
                    self.assertEqual(self.request(method, path, {}).status_code, 405)
                self.assertEqual(self.request("get", f"{path}/1").status_code, 404)

    def test_history_only_exposes_collection_operations(self):
        response = self.request("get", "me/viewing-history")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(
            self.request("delete", "me/viewing-history/clear").status_code, 204
        )
        self.assertEqual(self.request("delete", "me/viewing-history").status_code, 405)
        self.assertEqual(
            self.request("patch", "me/viewing-history", {}).status_code, 405
        )
        self.assertEqual(self.request("get", "me/viewing-history/1").status_code, 405)

    def test_receipt_route_accepts_signed_string_characters(self):
        response = self.client.get(
            "/api/v1/account-deletion-status/.invalid:receipt.with.dots/"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data["detail"], "This receipt is invalid or has expired."
        )
