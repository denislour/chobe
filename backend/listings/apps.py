from django.apps import AppConfig


class ListingsConfig(AppConfig):
    name = "listings"

    def ready(self):
        from listings.tasks import dispatch  # noqa: F401
