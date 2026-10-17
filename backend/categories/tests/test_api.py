from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError as ModelValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from rest_framework.test import APIClient

from accounts.tests.base import AccountAPITestCase
from categories.models import Category, CategoryAuditEvent, CategoryRevision


class CategoryTests(AccountAPITestCase):
    def setUp(self):
        super().setUp()
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save(update_fields=("is_staff", "is_superuser"))
        self.values = {
            "name": "Electronics",
            "slug": "electronics",
            "attributes": [
                {
                    "key": "storage_gb",
                    "label": "Storage",
                    "type": "integer",
                    "unit": "GB",
                    "min_value": 1,
                    "max_value": 2048,
                    "required": True,
                    "filterable": True,
                },
                {
                    "key": "tested",
                    "label": "Tested",
                    "type": "boolean",
                    "required": True,
                },
                {"key": "notes", "label": "Notes", "type": "text", "max_length": 20},
            ],
        }
        self.public = APIClient(enforce_csrf_checks=True)

    def create_category(self, values=None):
        response = self.request("post", "admin/categories", values or self.values)
        self.assertEqual(response.status_code, 201, response.data)
        return Category.objects.get(pk=response.data["id"])

    def publish(self, category):
        response = self.request(
            "post",
            f"admin/categories/{category.pk}/publish",
            {"version": category.version},
        )
        self.assertEqual(response.status_code, 200, response.data)
        category.refresh_from_db()
        return category

    def test_public_reads_only_published_snapshots_and_filterable_fields(self):
        category = self.create_category()
        self.assertEqual(self.public.get("/api/v1/categories/").data, [])
        self.assertEqual(
            self.public.get(f"/api/v1/categories/{category.pk}/").status_code, 404
        )
        self.publish(category)
        response = self.public.get(f"/api/v1/categories/{category.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["version"], 2)
        self.assertNotIn("restricted", response.data)
        self.assertNotIn("published", response.data)
        self.assertNotIn("actor", response.data)
        self.assertIn("no-store", response["Cache-Control"])
        facets = self.public.get(f"/api/v1/categories/{category.pk}/facets/")
        self.assertEqual(
            [field["key"] for field in facets.data["fields"]], ["storage_gb"]
        )

    def test_draft_edits_do_not_change_the_live_schema_or_old_revisions(self):
        category = self.publish(self.create_category())
        previous = CategoryRevision.objects.get(category=category)
        response = self.request(
            "patch",
            f"admin/categories/{category.pk}",
            {"version": 2, "name": "New electronics"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.public.get(f"/api/v1/categories/{category.pk}/").data["name"],
            "Electronics",
        )
        category.refresh_from_db()
        self.publish(category)
        self.assertEqual(
            self.public.get(f"/api/v1/categories/{category.pk}/").data["name"],
            "New electronics",
        )
        previous.refresh_from_db()
        self.assertEqual(previous.snapshot["name"], "Electronics")
        previous.snapshot["name"] = "Invalid edit"
        with self.assertRaises(ModelValidationError):
            previous.save()
        self.assertEqual(category.revisions.count(), 2)
        self.assertEqual(
            list(
                category.audit_events.order_by("created_at").values_list(
                    "action", flat=True
                )
            ),
            ["created", "published", "updated", "published"],
        )

    def test_stale_writes_and_public_validation_return_conflict(self):
        category = self.publish(self.create_category())
        response = self.request(
            "patch", f"admin/categories/{category.pk}", {"version": 1, "name": "Stale"}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            self.request(
                "post", f"admin/categories/{category.pk}/retire", {"version": 1}
            ).status_code,
            409,
        )
        response = self.public.post(
            f"/api/v1/categories/{category.pk}/validate-attributes/",
            {"version": 1, "attributes": {}},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(category.audit_events.count(), 2)

    def test_typed_attributes_preserve_false_and_reject_unknown_or_invalid_values(self):
        category = self.publish(self.create_category())
        url = f"/api/v1/categories/{category.pk}/validate-attributes/"
        response = self.public.post(
            url,
            {
                "version": category.version,
                "attributes": {"storage_gb": 128, "tested": False, "notes": "  Used  "},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["attributes"],
            {"storage_gb": 128, "tested": False, "notes": "Used"},
        )
        for values in (
            {"storage_gb": True, "tested": False},
            {"storage_gb": "128", "tested": False},
            {"storage_gb": 4096, "tested": False},
            {"storage_gb": 128},
            {"storage_gb": 128, "tested": False, "unknown": "x"},
        ):
            with self.subTest(values=values):
                response = self.public.post(
                    url,
                    {"version": category.version, "attributes": values},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("attributes", response.data)

    def test_draft_and_published_trees_are_validated_independently(self):
        parent = self.publish(self.create_category())
        child = self.publish(
            self.create_category(
                {"name": "Phones", "slug": "phones", "parent": str(parent.pk)}
            )
        )
        cycle = self.request(
            "patch",
            f"admin/categories/{parent.pk}",
            {"version": parent.version, "parent": str(child.pk)},
        )
        self.assertEqual(cycle.status_code, 400)
        blocked = self.request(
            "post", f"admin/categories/{parent.pk}/retire", {"version": parent.version}
        )
        self.assertEqual(blocked.status_code, 400)
        response = self.request(
            "post", f"admin/categories/{child.pk}/retire", {"version": child.version}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.public.get(f"/api/v1/categories/{child.pk}/").status_code, 404
        )
        response = self.request(
            "post", f"admin/categories/{parent.pk}/retire", {"version": parent.version}
        )
        self.assertEqual(response.status_code, 200)

    def test_restricted_categories_and_unpublished_parents_cannot_be_published(self):
        parent = self.create_category()
        child = self.create_category(
            {"name": "Phones", "slug": "phones", "parent": str(parent.pk)}
        )
        self.assertEqual(
            self.request(
                "post",
                f"admin/categories/{child.pk}/publish",
                {"version": child.version},
            ).status_code,
            400,
        )
        category = self.create_category(
            {"name": "Restricted", "slug": "restricted", "restricted": True}
        )
        self.assertEqual(
            self.request(
                "post",
                f"admin/categories/{category.pk}/publish",
                {"version": category.version},
            ).status_code,
            400,
        )
        self.assertFalse(CategoryRevision.objects.exists())

    def test_field_definitions_reject_duplicates_unknown_fields_and_incompatible_reuse(
        self,
    ):
        for attributes in (
            [{"key": "x", "label": "X", "type": "text"}] * 2,
            [{"key": "constructor", "label": "Invalid key", "type": "text"}],
            [{"key": "x", "label": "X", "type": "select", "choices": []}],
            [{"key": "x", "label": "X", "type": "text", "secret": True}],
            [
                {
                    "key": "x",
                    "label": "X",
                    "type": "integer",
                    "min_value": 10,
                    "max_value": 1,
                }
            ],
        ):
            with self.subTest(attributes=attributes):
                self.assertEqual(
                    self.request(
                        "post",
                        "admin/categories",
                        self.values | {"attributes": attributes},
                    ).status_code,
                    400,
                )
        category = self.publish(self.create_category())
        changed = [{"key": "storage_gb", "label": "Storage", "type": "text"}]
        self.assertEqual(
            self.request(
                "patch",
                f"admin/categories/{category.pk}",
                {"version": category.version, "attributes": changed},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.request(
                "patch",
                f"admin/categories/{category.pk}",
                {"version": category.version, "slug": "changed"},
            ).status_code,
            400,
        )

    def test_publishing_checks_the_live_parent_tree_not_only_the_draft_tree(self):
        parent = self.publish(self.create_category())
        child = self.publish(
            self.create_category(
                {"name": "Phones", "slug": "phones", "parent": str(parent.pk)}
            )
        )
        changed = self.request(
            "patch",
            f"admin/categories/{child.pk}",
            {"version": child.version, "parent": None},
        )
        self.assertEqual(changed.status_code, 200)
        changed = self.request(
            "patch",
            f"admin/categories/{parent.pk}",
            {"version": parent.version, "parent": str(child.pk)},
        )
        self.assertEqual(changed.status_code, 200)
        parent.refresh_from_db()
        response = self.request(
            "post", f"admin/categories/{parent.pk}/publish", {"version": parent.version}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.public.get(f"/api/v1/categories/{parent.pk}/").data["parent"], None
        )
        self.assertEqual(
            self.public.get(f"/api/v1/categories/{child.pk}/").data["parent"],
            str(parent.pk),
        )

    def test_removed_attribute_keys_keep_their_published_type_and_unit(self):
        category = self.publish(self.create_category())
        self.assertEqual(
            self.request(
                "patch",
                f"admin/categories/{category.pk}",
                {"version": category.version, "attributes": []},
            ).status_code,
            200,
        )
        category.refresh_from_db()
        self.publish(category)
        changed = [{"key": "storage_gb", "label": "Storage", "type": "text"}]
        response = self.request(
            "patch",
            f"admin/categories/{category.pk}",
            {"version": category.version, "attributes": changed},
        )
        self.assertEqual(response.status_code, 400)

    def test_category_tree_is_limited_to_four_levels(self):
        parent = self.publish(self.create_category())
        for level in range(2, 5):
            parent = self.publish(
                self.create_category(
                    {
                        "name": f"Level {level}",
                        "slug": f"level-{level}",
                        "parent": str(parent.pk),
                    }
                )
            )
        response = self.request(
            "post",
            "admin/categories",
            {"name": "Level five", "slug": "level-five", "parent": str(parent.pk)},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Category.objects.count(), 4)

    def test_select_and_number_values_use_canonical_choices_and_numeric_bounds(self):
        category = self.publish(
            self.create_category(
                {
                    "name": "Furniture",
                    "slug": "furniture",
                    "attributes": [
                        {
                            "key": "material",
                            "label": "Material",
                            "type": "select",
                            "required": True,
                            "choices": [{"value": "wood", "label": "Wood"}],
                        },
                        {
                            "key": "weight_kg",
                            "label": "Weight",
                            "type": "number",
                            "unit": "kg",
                            "min_value": 0.1,
                            "max_value": 10,
                        },
                    ],
                }
            )
        )
        url = f"/api/v1/categories/{category.pk}/validate-attributes/"
        good = {"material": "wood", "weight_kg": 1.5}
        response = self.public.post(
            url, {"version": category.version, "attributes": good}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["attributes"], good)
        for values in (
            good | {"material": "Wood"},
            good | {"weight_kg": True},
            good | {"weight_kg": 0},
        ):
            with self.subTest(values=values):
                self.assertEqual(
                    self.public.post(
                        url,
                        {"version": category.version, "attributes": values},
                        format="json",
                    ).status_code,
                    400,
                )

    def test_category_management_requires_permissions_and_csrf(self):
        self.assertEqual(self.public.get("/api/v1/admin/categories/").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/v1/admin/categories/", self.values, format="json"
            ).status_code,
            403,
        )
        self.client.force_login(self.other)
        self.assertEqual(
            self.request("post", "admin/categories", self.values).status_code, 403
        )
        self.other.is_staff = True
        self.other.save(update_fields=("is_staff",))
        self.other.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="categories",
                codename__in=("view_category", "add_category", "change_category"),
            )
        )
        category = self.create_category()
        self.assertEqual(
            self.request(
                "post",
                f"admin/categories/{category.pk}/publish",
                {"version": category.version},
            ).status_code,
            403,
        )
        self.assertFalse(
            self.request("get", "admin/categories/capabilities").data["publish"]
        )
        self.assertFalse(CategoryRevision.objects.exists())

    def test_router_blocks_unavailable_crud_and_schema_keeps_only_supported_operations(
        self,
    ):
        category = self.publish(self.create_category())
        for method in ("put", "delete"):
            self.assertEqual(
                self.request(method, f"admin/categories/{category.pk}", {}).status_code,
                405,
            )
        self.assertEqual(
            self.request("post", "categories", self.values).status_code, 405
        )
        self.assertEqual(
            self.request("patch", f"categories/{category.pk}", {}).status_code, 405
        )
        paths = self.client.get(
            "/api/v1/schema/", HTTP_ACCEPT="application/json"
        ).json()["paths"]
        self.assertEqual(set(paths["/api/v1/categories/"]), {"get"})
        self.assertIn("/api/v1/admin/categories/{id}/publish/", paths)

    @override_settings(DEMO_MODE=True)
    def test_demo_seed_is_idempotent_and_never_overwrites_existing_categories(self):
        category = self.create_category()
        call_command("seed_demo_categories", username=self.user.username, verbosity=0)
        count = Category.objects.count()
        call_command("seed_demo_categories", username=self.user.username, verbosity=0)
        self.assertEqual(Category.objects.count(), count)
        category.refresh_from_db()
        self.assertEqual(category.status, Category.Status.DRAFT)
        self.assertEqual(category.name, "Electronics")

    @override_settings(DEMO_MODE=False)
    def test_demo_seed_requires_demo_mode(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo_categories", username=self.user.username)
        self.assertFalse(CategoryAuditEvent.objects.exists())

    def test_patch_attribute_entries_apply_defaults_and_require_complete_definitions(
        self,
    ):
        category = self.create_category()
        response = self.request(
            "patch",
            f"admin/categories/{category.pk}",
            {
                "version": category.version,
                "attributes": [{"key": "color", "label": "Color", "type": "text"}],
            },
        )
        self.assertEqual(response.status_code, 200)
        field = response.data["attributes"][0]
        self.assertEqual(field["choices"], [])
        self.assertFalse(field["required"])
        self.assertEqual(field["unit"], "")
        category.refresh_from_db()
        response = self.request(
            "patch",
            f"admin/categories/{category.pk}",
            {"version": category.version, "attributes": [{"key": "color"}]},
        )
        self.assertEqual(response.status_code, 400)
        category.refresh_from_db()
        self.publish(category)
        self.assertEqual(category.published["attributes"][0]["max_length"], 200)
