from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from accounts.constants import DEMO_ADMIN_PASSWORD
from accounts.models import User
from accounts.tests.base import AccountAPITestCase
from shops.models import Shop, ShopFollow
from shops.services.management import create_shop


class FollowingTests(AccountAPITestCase):
    def setUp(self):
        super().setUp()
        self.shop = create_shop(
            self.other,
            {
                "name": "Moc Home",
                "slug": "moc-home",
                "area": "Ha Noi",
                "description": "Furniture.",
            },
        )
        self.path = f"me/followed-shops/{self.shop.pk}"

    def test_follow_and_unfollow_are_idempotent_and_scoped_to_the_viewer(self):
        for _ in range(2):
            self.assertEqual(self.request("put", self.path, {}).status_code, 204)
        self.assertEqual(ShopFollow.objects.filter(user=self.user).count(), 1)
        foreign = ShopFollow.objects.create(user=self.other, shop=self.shop)
        response = self.request("get", "me/followed-shops")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertTrue(response.data["results"][0]["is_following"])
        for _ in range(2):
            self.assertEqual(self.request("delete", self.path).status_code, 204)
        self.assertFalse(ShopFollow.objects.filter(user=self.user).exists())
        self.assertTrue(ShopFollow.objects.filter(pk=foreign.pk).exists())
        self.assertEqual(self.request("get", "me/followed-shops").data["count"], 0)

    def test_follow_requires_authentication_and_csrf(self):
        guest = APIClient(enforce_csrf_checks=True)
        self.assertEqual(guest.get("/api/v1/me/followed-shops/").status_code, 403)
        self.assertEqual(guest.put(f"/api/v1/{self.path}/", {}).status_code, 403)
        self.assertEqual(self.client.put(f"/api/v1/{self.path}/", {}).status_code, 403)
        self.request("put", self.path, {})
        self.assertEqual(self.client.delete(f"/api/v1/{self.path}/").status_code, 403)
        self.assertEqual(ShopFollow.objects.filter(user=self.user).count(), 1)

    def test_following_resource_only_exposes_list_put_and_delete(self):
        self.assertEqual(self.request("get", self.path).status_code, 405)
        self.assertEqual(self.request("patch", self.path, {}).status_code, 405)
        self.assertEqual(self.request("post", "me/followed-shops", {}).status_code, 405)
        self.assertEqual(
            self.request("put", "me/followed-shops/invalid-id", {}).status_code, 404
        )
        self.assertFalse(ShopFollow.objects.exists())

    def test_hidden_shop_cannot_be_followed_but_existing_follow_can_be_removed(self):
        for status in (Shop.Status.PAUSED, Shop.Status.SUSPENDED, Shop.Status.CLOSED):
            with self.subTest(status=status):
                Shop.objects.filter(pk=self.shop.pk).update(status=status)
                self.assertEqual(self.request("put", self.path, {}).status_code, 404)
                ShopFollow.objects.get_or_create(user=self.user, shop=self.shop)
                self.assertEqual(
                    self.request("get", "me/followed-shops").data["count"], 0
                )
                self.assertEqual(self.request("delete", self.path).status_code, 204)
        Shop.objects.filter(pk=self.shop.pk).update(status=Shop.Status.ACTIVE)
        self.other.is_active = False
        self.other.save(update_fields=("is_active",))
        self.assertEqual(self.request("put", self.path, {}).status_code, 404)

    def test_follow_uniqueness_is_enforced_by_the_database(self):
        ShopFollow.objects.create(user=self.user, shop=self.shop)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ShopFollow.objects.create(user=self.user, shop=self.shop)

    def test_followed_shops_are_paginated_without_other_users_follows(self):
        owners = User.objects.bulk_create(
            [User(username=f"seller-{i}") for i in range(21)]
        )
        shops = Shop.objects.bulk_create(
            [
                Shop(
                    owner=owner,
                    name=owner.username,
                    slug=owner.username,
                    area="Ha Noi",
                    description="Shop.",
                )
                for owner in owners
            ]
        )
        ShopFollow.objects.bulk_create(
            [ShopFollow(user=self.user, shop=shop) for shop in shops]
        )
        ShopFollow.objects.create(user=self.other, shop=self.shop)
        response = self.request("get", "me/followed-shops")
        self.assertEqual(response.data["count"], 21)
        self.assertEqual(len(response.data["results"]), 20)
        second = self.client.get("/api/v1/me/followed-shops/?page=2")
        self.assertEqual(len(second.data["results"]), 1)
        self.assertTrue(second.data["previous"])
        self.assertIsNone(second.data["next"])
        self.assertEqual(
            self.client.get("/api/v1/me/followed-shops/?page=0").status_code, 404
        )

    def test_export_and_account_deletion_include_follows(self):
        self.request("put", self.path, {})
        response = self.request("post", "me/data-exports", {})
        self.run_worker()
        payload = self.request(
            "get", f"me/data-exports/{response.data['job_id']}/download"
        ).json()
        self.assertEqual(len(payload["followed_shops"]), 1)
        self.assertEqual(payload["followed_shops"][0]["shop_id"], str(self.shop.pk))
        self.assertEqual(set(payload["followed_shops"][0]), {"shop_id", "created_at"})
        deleted = self.request(
            "post",
            "me/deletion-requests",
            {"password": DEMO_ADMIN_PASSWORD, "confirmation": "DELETE"},
        )
        self.assertEqual(deleted.status_code, 202)
        self.run_worker()
        self.assertFalse(ShopFollow.objects.filter(user_id=self.user.pk).exists())
        self.assertTrue(Shop.objects.filter(pk=self.shop.pk).exists())

    def test_deleting_a_shop_owner_removes_incoming_follows(self):
        follow = ShopFollow.objects.create(user=self.user, shop=self.shop)
        self.other.delete()
        self.assertFalse(ShopFollow.objects.filter(pk=follow.pk).exists())
