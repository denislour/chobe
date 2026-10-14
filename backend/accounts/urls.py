from django.urls import include, path
from rest_framework.routers import SimpleRouter

from accounts.views.auth import AuthViewSet

router = SimpleRouter()
router.register("auth", AuthViewSet, basename="auth")
urlpatterns = [path("", include(router.urls))]
