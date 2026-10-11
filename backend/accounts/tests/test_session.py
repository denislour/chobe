from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.constants import DEMO_ADMIN_PASSWORD
from accounts.models import User


class SessionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member")
        self.client = APIClient(enforce_csrf_checks=True)

    def post_logout(self):
        self.client.get("/api/v1/auth/csrf/")
        return self.client.post(
            "/api/v1/auth/logout/",
            HTTP_X_XSRF_TOKEN=self.client.cookies[settings.CSRF_COOKIE_NAME].value,
        )

    def test_anonymous_session_returns_null_without_creating_a_session(self):
        response = self.client.get("/api/v1/auth/session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"user": None})
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertIn("no-store", response["Cache-Control"])

    def test_session_returns_current_user_from_cookie(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/v1/auth/session/", {"user_id": 999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {"user": {"id": self.user.pk, "username": "member"}}
        )

    def test_expired_session_returns_null(self):
        self.client.force_login(self.user)
        Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get("/api/v1/auth/session/").data, {"user": None})

    def test_real_login_is_restored_by_a_new_client_and_logout_clears_it(self):
        self.user.set_password(DEMO_ADMIN_PASSWORD)
        self.user.save()
        self.client.get("/api/v1/auth/csrf/")
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": self.user.username, "password": DEMO_ADMIN_PASSWORD},
            format="json",
            HTTP_X_XSRF_TOKEN=self.client.cookies[settings.CSRF_COOKIE_NAME].value,
        )
        self.assertEqual(response.status_code, 200)
        cookies = self.client.cookies
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.cookies = cookies
        self.assertEqual(
            self.client.get("/api/v1/auth/session/").data["user"]["id"], self.user.pk
        )
        self.assertEqual(self.post_logout().status_code, 204)
        self.assertEqual(self.client.get("/api/v1/auth/session/").data, {"user": None})

    def test_invalid_cookie_returns_null(self):
        self.client.cookies[settings.SESSION_COOKIE_NAME] = "invalid"
        self.assertEqual(self.client.get("/api/v1/auth/session/").data, {"user": None})

    def test_inactive_user_session_returns_null(self):
        self.client.force_login(self.user)
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.get("/api/v1/auth/session/").data, {"user": None})

    def test_logout_revokes_session_and_old_cookie_cannot_restore_it(self):
        self.client.force_login(self.user)
        old_key = self.client.session.session_key
        response = self.post_logout()
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response.cookies[settings.SESSION_COOKIE_NAME]["max-age"], 0)
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())
        self.client.cookies[settings.SESSION_COOKIE_NAME] = old_key
        self.assertEqual(self.client.get("/api/v1/auth/session/").data, {"user": None})

    def test_anonymous_logout_can_be_repeated(self):
        for _ in range(2):
            self.assertEqual(self.post_logout().status_code, 204)

    def test_logout_without_csrf_does_not_revoke_session(self):
        self.client.force_login(self.user)
        response = self.client.post("/api/v1/auth/logout/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_cross_origin_logout_does_not_revoke_session(self):
        self.client.force_login(self.user)
        self.client.get("/api/v1/auth/csrf/")
        response = self.client.post(
            "/api/v1/auth/logout/",
            HTTP_X_XSRF_TOKEN=self.client.cookies[settings.CSRF_COOKIE_NAME].value,
            HTTP_ORIGIN="https://attacker.example",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_session_and_logout_contracts_are_in_openapi(self):
        paths = self.client.get(
            "/api/v1/schema/", HTTP_ACCEPT="application/json"
        ).json()["paths"]
        session = paths["/api/v1/auth/session/"]["get"]
        logout = paths["/api/v1/auth/logout/"]["post"]
        self.assertEqual(
            session["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/Session",
        )
        self.assertNotIn("requestBody", logout)
        self.assertNotIn("content", logout["responses"]["204"])
        self.assertTrue(
            next(p for p in logout["parameters"] if p["name"] == "X-XSRF-TOKEN")[
                "required"
            ]
        )
