from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .schema import AuthSchema
from .serializers import LoginSerializer, LoginUserSerializer
from .throttles import LoginAccountThrottle, LoginIPThrottle


@method_decorator(never_cache, name="dispatch")
class AuthViewSet(GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer
    schema = AuthSchema()

    def initial(self, request, *args, **kwargs):
        if self.action in ("login", "logout"):
            SessionAuthentication().enforce_csrf(request)
        super().initial(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def csrf(self, request):
        get_token(request)
        return Response(status=204)

    @action(
        detail=False,
        methods=["post"],
        authentication_classes=(),
        throttle_classes=[LoginIPThrottle, LoginAccountThrottle],
    )
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return Response(LoginUserSerializer(user).data)

    @action(detail=False, methods=["get"])
    def session(self, request):
        user = (
            LoginUserSerializer(request.user).data
            if request.user.is_authenticated
            else None
        )
        return Response({"user": user})

    @action(detail=False, methods=["post"])
    def logout(self, request):
        logout(request)
        return Response(status=204)
