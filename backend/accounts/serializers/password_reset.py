from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import password_changed
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from accounts.models import User


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
            user = User.objects.get(pk=urlsafe_base64_decode(attrs["uid"]).decode())
        except ValueError, TypeError, OverflowError, User.DoesNotExist:
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
        form = validated_data["form"]
        old_password = form.user.password
        user = form.save(commit=False)
        if not User.objects.filter(
            pk=user.pk,
            password=old_password,
            email=user.email,
            last_login=user.last_login,
            is_active=True,
        ).update(password=user.password):
            raise serializers.ValidationError(
                "This password reset link has already been used. Request a new link."
            )
        password_changed(validated_data["password"], user)
        return user
