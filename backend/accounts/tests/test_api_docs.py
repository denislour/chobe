import json

from django.test import TestCase


class ApiDocsTests(TestCase):
    def test_schema_endpoint_returns_api_metadata(self):
        response = self.client.get("/api/v1/schema/", HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["info"]["title"], "Chobe API")

    def test_swagger_ui_is_available(self):
        response = self.client.get("/api/v1/docs/")

        self.assertEqual(response.status_code, 200)
