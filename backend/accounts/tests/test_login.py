from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.constants import DEMO_ADMIN_PASSWORD, DEMO_ADMIN_USERNAME
from accounts.models import User


class LoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = User.objects.create_user(
            username=DEMO_ADMIN_USERNAME,
            email="admin@example.com",
            password=DEMO_ADMIN_PASSWORD,
        )
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.get("/api/v1/auth/csrf/")
        self.token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        self.credentials = {
            "username": DEMO_ADMIN_USERNAME,
            "password": DEMO_ADMIN_PASSWORD,
        }

    def post_login(self, **kwargs):
        return self.client.post(
            "/api/v1/auth/login/",
            kwargs or self.credentials,
            format="json",
            HTTP_X_XSRF_TOKEN=self.client.cookies[settings.CSRF_COOKIE_NAME].value,
        )

    def test_login_creates_an_opaque_session_and_rotates_csrf(self):
        session = self.client.session
        session["before_login"] = True
        session.save()
        old_key = session.session_key
        response = self.post_login()
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {"id": self.user.pk, "username": self.user.username}
        )
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
        self.assertNotEqual(cookie.value, old_key)
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(int(cookie["max-age"]), 8 * 60 * 60)
        self.assertNotEqual(
            response.cookies[settings.CSRF_COOKIE_NAME].value, self.token
        )
        self.assertIn("no-store", response["Cache-Control"])

    def test_email_login_is_case_insensitive(self):
        self.assertEqual(
            self.post_login(
                username="ADMIN@example.com", password=DEMO_ADMIN_PASSWORD
            ).status_code,
            200,
        )

    def test_username_containing_at_can_login(self):
        self.user.username = "n@m"
        self.user.save()
        response = self.post_login(username="n@m", password=DEMO_ADMIN_PASSWORD)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.user.pk)

    def test_same_user_matching_username_and_email_can_login(self):
        self.user.username = self.user.email
        self.user.save()
        response = self.post_login(
            username=self.user.email, password=DEMO_ADMIN_PASSWORD
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.user.pk)

    def test_identifier_matching_two_users_is_rejected(self):
        User.objects.create_user(
            username=self.user.email,
            email="other@example.com",
            password=DEMO_ADMIN_PASSWORD,
        )
        response = self.post_login(
            username=self.user.email, password=DEMO_ADMIN_PASSWORD
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["non_field_errors"], ["Invalid username or password."]
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_invalid_credentials_use_the_same_error(self):
        for username in (DEMO_ADMIN_USERNAME, "missing", "missing@example.com"):
            with self.subTest(username=username):
                response = self.post_login(username=username, password="wrong")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.data["non_field_errors"], ["Invalid username or password."]
                )
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.post_login()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["non_field_errors"], ["Invalid username or password."]
        )

    def test_login_requires_csrf_even_for_anonymous_clients(self):
        for token in (None, "x" * 32):
            with self.subTest(token=token):
                headers = {"HTTP_X_XSRF_TOKEN": token} if token else {}
                response = self.client.post(
                    "/api/v1/auth/login/", self.credentials, format="json", **headers
                )
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_cross_origin_login_is_rejected(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            self.credentials,
            format="json",
            HTTP_X_XSRF_TOKEN=self.token,
            HTTP_ORIGIN="https://attacker.example",
        )
        self.assertEqual(response.status_code, 403)

    def test_proxy_origin_can_login(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            self.credentials,
            format="json",
            HTTP_X_XSRF_TOKEN=self.token,
            HTTP_ORIGIN="http://localhost:4200",
            HTTP_HOST="localhost:4200",
        )
        self.assertEqual(response.status_code, 200)

    def test_malformed_input_is_rejected(self):
        for payload in (
            {},
            {"username": 123, "password": None},
            [],
            {"username": "a" * 255, "password": "a"},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/api/v1/auth/login/",
                    payload,
                    format="json",
                    HTTP_X_XSRF_TOKEN=self.token,
                )
                self.assertEqual(response.status_code, 400)

    def test_account_throttle_cannot_be_bypassed_by_changing_ip(self):
        for index in range(5):
            self.client.defaults["REMOTE_ADDR"] = f"192.0.2.{index}"
            self.assertEqual(
                self.post_login(username="missing", password="wrong").status_code, 400
            )
        response = self.post_login(username=" MISSING ", password="wrong")
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    def test_ip_throttle_cannot_be_bypassed_by_changing_identifier(self):
        for index in range(20):
            self.client.defaults["HTTP_X_FORWARDED_FOR"] = f"192.0.2.{index}"
            self.assertEqual(
                self.post_login(
                    username=f"missing-{index}", password="wrong"
                ).status_code,
                400,
            )
        self.assertEqual(self.post_login().status_code, 429)

    @override_settings(DEBUG=False, SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_https_cookies_are_secure(self):
        self.client.get("/api/v1/auth/csrf/", secure=True)
        response = self.client.post(
            "/api/v1/auth/login/",
            self.credentials,
            format="json",
            secure=True,
            HTTP_X_XSRF_TOKEN=self.client.cookies[settings.CSRF_COOKIE_NAME].value,
            HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies[settings.SESSION_COOKIE_NAME]["secure"])
        self.assertTrue(response.cookies[settings.CSRF_COOKIE_NAME]["secure"])

    def test_login_contract_is_in_openapi(self):
        schema = self.client.get(
            "/api/v1/schema/", HTTP_ACCEPT="application/json"
        ).json()
        login = schema["paths"]["/api/v1/auth/login/"]["post"]
        csrf = schema["paths"]["/api/v1/auth/csrf/"]["get"]
        self.assertEqual(
            login["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/Login",
        )
        self.assertEqual(
            login["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/LoginUser",
        )
        self.assertEqual(login["parameters"][0]["name"], "X-XSRF-TOKEN")
        self.assertEqual(login["parameters"][0]["in"], "header")
        self.assertTrue(login["parameters"][0]["required"])
        self.assertNotIn("content", csrf["responses"]["204"])
        self.assertNotIn("parameters", csrf)
        self.assertNotIn("/api/v1/auth/", schema["paths"])
