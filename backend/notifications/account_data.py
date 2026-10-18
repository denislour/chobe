from rest_framework import serializers

from notifications.models import NotificationPreference


class NotificationPreferenceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ("inbox", "email")
        read_only_fields = fields
