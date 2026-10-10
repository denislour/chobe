from django.test import TestCase

from accounts.models import User


class AdminTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(username="admin", password="abc123ABC!!!")

    def test_admin_pages_render_with_unfold(self):
        user = User.objects.get(username="admin")
        self.client.force_login(user)
        for path in (
            "/admin/",
            "/admin/accounts/user/add/",
            f"/admin/accounts/user/{user.pk}/change/",
            f"/admin/accounts/user/{user.pk}/password/",
            "/admin/auth/group/add/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "unfold/css/styles.css")

    def test_root_redirects_to_admin(self):
        self.assertRedirects(
            self.client.get("/"), "/admin/", fetch_redirect_response=False
        )
