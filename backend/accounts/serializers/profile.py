from typing import ClassVar

from django.urls import reverse
from rest_framework import serializers

from accounts.models import Profile
from accounts.services.profile import clean_avatar, update_profile


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    phone = serializers.RegexField(
        r"^\+[1-9]\d{7,14}$", allow_blank=True, required=False
    )
    avatar_url = serializers.SerializerMethodField()
    avatar = serializers.FileField(write_only=True, required=False)
    remove_avatar = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = Profile
        fields = (
            "display_name",
            "email",
            "username",
            "area",
            "bio",
            "phone",
            "avatar_url",
            "avatar",
            "remove_avatar",
            "version",
            "updated_at",
        )
        read_only_fields = ("updated_at",)
        extra_kwargs: ClassVar[dict] = {
            "version": {"min_value": 1, "required": True},
        }

    def get_avatar_url(self, obj) -> str | None:
        if not obj.avatar:
            return None
        return f"{reverse('profile-avatar')}?version={obj.version}"

    def validate_avatar(self, value):
        return clean_avatar(value)

    def validate(self, attrs):
        if "version" not in attrs:
            raise serializers.ValidationError({"version": ["This field is required."]})
        if attrs.get("remove_avatar") and "avatar" in attrs:
            raise serializers.ValidationError(
                {"avatar": ["Choose upload or removal, not both."]}
            )
        return attrs

    def update(self, instance, validated_data):
        return update_profile(instance, validated_data)
