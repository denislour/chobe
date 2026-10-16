from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.schemas.auth import AuthSchema
from accounts.schemas.password_reset import PasswordResetSchema
from accounts.serializers.login import LoginSerializer
from accounts.serializers.password_reset import (
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)
from accounts.serializers.register import RegisterSerializer
from accounts.serializers.session import AuthUserSerializer
from accounts.tasks.email import send_password_reset_email
from accounts.throttles import (
    ForgotPasswordAccountThrottle,
    ForgotPasswordIPThrottle,
    LoginAccountThrottle,
    LoginIPThrottle,
    RegisterIPThrottle,
    ResetPasswordIPThrottle,
)


@method_decorator(never_cache, name="dispatch")
class AuthViewSet(ModelViewSet):
    permission_classes = (AllowAny,)
    serializer_class = AuthUserSerializer
    schema = AuthSchema()

    def get_permissions(self):
        actions = self.action_map.values() if self.action == "metadata" else (self.action,)
        if not any(
            action in (
                "login",
                "register",
                "session",
                "logout",
                "forgot_password",
                "reset_password",
            )
            for action in actions
        ):
            raise MethodNotAllowed(self.request.method)
        return super().get_permissions()

    def initial(self, request, *args, **kwargs):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            SessionAuthentication().enforce_csrf(request)
        super().initial(request, *args, **kwargs)

    @action(
        detail=False,
        methods=["post"],
        serializer_class=LoginSerializer,
        schema=AuthSchema(),
        authentication_classes=(),
        throttle_classes=[LoginIPThrottle, LoginAccountThrottle],
    )
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return Response(AuthUserSerializer(user).data)

    @action(
        detail=False,
        methods=["post"],
        serializer_class=RegisterSerializer,
        schema=AuthSchema(),
        throttle_classes=[RegisterIPThrottle],
    )
    def register(self, request):
        if request.user.is_authenticated:
            return Response(
                {"non_field_errors": ["Log out before creating another account."]},
                status=400,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(AuthUserSerializer(user).data, status=201)

    @action(detail=False, methods=["get"], schema=AuthSchema())
    def session(self, request):
        get_token(request)
        user = (
            AuthUserSerializer(request.user).data
            if request.user.is_authenticated
            else None
        )
        return Response({"user": user})

    @action(detail=False, methods=["post"], schema=AuthSchema())
    def logout(self, request):
        logout(request)
        return Response(status=204)

    @action(
        detail=False,
        methods=["post"],
        url_path="forgot-password",
        schema=PasswordResetSchema(),
        serializer_class=ForgotPasswordSerializer,
        throttle_classes=[
            ForgotPasswordIPThrottle,
            ForgotPasswordAccountThrottle,
        ],
    )
    def forgot_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        send_password_reset_email.enqueue(serializer.validated_data["email"])
        return Response(status=202)

    @action(
        detail=False,
        methods=["post"],
        url_path="reset-password",
        schema=PasswordResetSchema(),
        serializer_class=ResetPasswordSerializer,
        throttle_classes=[ResetPasswordIPThrottle],
    )
    def reset_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logout(request)
        return Response(status=204)
