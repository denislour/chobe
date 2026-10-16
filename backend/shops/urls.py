from django.urls import path

from shops.views import ShopViewSet

urlpatterns = [
    path("me/shop/", ShopViewSet.as_view({"get": "mine"})),
    path("shops/", ShopViewSet.as_view({"post": "create"})),
    path("shops/<uuid:pk>/", ShopViewSet.as_view({"patch": "partial_update"})),
    path("shops/<slug:slug>/preview/", ShopViewSet.as_view({"get": "preview"})),
    path(
        "shops/<uuid:pk>/images/<str:kind>/",
        ShopViewSet.as_view({"get": "image"}),
        name="shop-image",
    ),
]
