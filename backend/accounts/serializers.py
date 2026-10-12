from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import User


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=254)
    password = serializers.CharField(
        max_length=128, trim_whitespace=False, write_only=True
    )

    def validate(self, attrs):
        identifier = attrs["username"]
        matches = list(
            User.objects.filter(
                Q(username=identifier) | Q(email__iexact=identifier)
            ).values_list("username", flat=True)[:2]
        )
        username = matches[0] if len(matches) == 1 else ""
        user = authenticate(
            request=self.context["request"],
            username=username,
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid username or password.")
        attrs["user"] = user
        return attrs


class LoginUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")


class SessionSerializer(serializers.Serializer):
    user = LoginUserSerializer(allow_null=True)


class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=150, validators=[UnicodeUsernameValidator()]
    )
    email = serializers.EmailField(
        max_length=254,
        validators=[
            UniqueValidator(
                User.objects.all(),
                lookup="iexact",
                message="A user with this email already exists.",
            )
        ],
    )
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
        validated_data.pop("accept_terms")
        try:
            with transaction.atomic():
                return User.objects.create_user(**validated_data)
        except IntegrityError as error:
            raise serializers.ValidationError(
                {"non_field_errors": ["Username or email is already in use."]}
            ) from error
