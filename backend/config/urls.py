from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import SimpleRouter

from accounts.views import LoginViewSet

router = SimpleRouter()
router.register("auth", LoginViewSet, basename="auth")

urlpatterns = [
    path("api/v1/", include(router.urls)),
    path("", RedirectView.as_view(pattern_name="admin:index")),
    path("admin/", admin.site.urls),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
