from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import serializers

from accounts.models import User


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
