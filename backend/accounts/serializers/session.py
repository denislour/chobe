from rest_framework import serializers

from accounts.models import User


class AuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")


class SessionSerializer(serializers.Serializer):
    user = AuthUserSerializer(allow_null=True)
