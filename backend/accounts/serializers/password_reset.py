from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from accounts.models import User
from accounts.services.auth import reset_password


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=128, write_only=True)
    token = serializers.CharField(max_length=128, write_only=True)
    password = serializers.CharField(
        max_length=128, trim_whitespace=False, write_only=True
    )
    password_confirm = serializers.CharField(
        max_length=128, trim_whitespace=False, write_only=True
    )

    def validate(self, attrs):
        try:
            user = User.objects.filter(
                pk=urlsafe_base64_decode(attrs["uid"]).decode()
            ).first()
        except ValueError, TypeError, OverflowError:
            user = None
        if (
            user is None
            or not user.is_active
            or not user.has_usable_password()
            or not default_token_generator.check_token(user, attrs["token"])
        ):
            raise serializers.ValidationError(
                "This password reset link is invalid or has expired. Request a new link."
            )
        form = SetPasswordForm(
            user,
            {
                "new_password1": attrs["password"],
                "new_password2": attrs["password_confirm"],
            },
        )
        if not form.is_valid():
            raise serializers.ValidationError(
                {"password_confirm": list(form.errors["new_password2"])}
            )
        attrs["form"] = form
        return attrs

    def create(self, validated_data):
        return reset_password(validated_data["form"].user, validated_data["password"])
