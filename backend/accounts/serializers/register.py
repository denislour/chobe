from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from rest_framework import serializers

from accounts.models import User
from accounts.services.auth import register_account


class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=150, validators=[UnicodeUsernameValidator()]
    )
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        max_length=128, trim_whitespace=False, write_only=True
    )
    accept_terms = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "accept_terms")

    def validate_username(self, value):
        value = User.normalize_username(value)
        self.fields["username"].run_validators(value)
        if "@" in value:
            raise serializers.ValidationError(
                "Use a username without @. Enter your email separately."
            )
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return value

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "This email is already used as a username."
            )
        return value

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError(
                "Accept the terms and privacy policy to continue."
            )
        return value

    def validate(self, attrs):
        user = User(
            username=attrs["username"],
            email=attrs["email"],
        )
        try:
            validate_password(attrs["password"], user)
        except ValidationError as error:
            raise serializers.ValidationError({"password": error.messages}) from error
        return attrs

    def create(self, validated_data):
        return register_account(validated_data)
