from rest_framework import serializers

from accounts.models import User


class LoginUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")


class SessionSerializer(serializers.Serializer):
    user = LoginUserSerializer(allow_null=True)
