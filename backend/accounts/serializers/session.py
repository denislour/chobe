from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class AuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username")


class SessionSerializer(serializers.Serializer):
    user = AuthUserSerializer(allow_null=True)
