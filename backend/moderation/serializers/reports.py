from typing import ClassVar

from django.db import transaction
from rest_framework import serializers

from discovery.queries import public_listings
from listings.models import (
    Report,
    ReportDecision,
)
from shops.models import Shop


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = (
            "id",
            "listing",
            "shop",
            "reason",
            "description",
            "status",
            "response",
            "version",
            "created_at",
        )
        read_only_fields = ("id", "status", "response", "version", "created_at")

    def validate(self, attrs):
        if bool(attrs.get("listing")) == bool(attrs.get("shop")):
            raise serializers.ValidationError(
                "Choose exactly one listing or shop to report."
            )
        if (
            attrs.get("listing")
            and not public_listings().filter(pk=attrs["listing"].pk).exists()
        ):
            raise serializers.ValidationError(
                {"listing": ["This listing is not available."]}
            )
        shop = attrs.get("shop")
        if (
            shop
            and not Shop.objects.filter(
                pk=shop.pk, status="active", owner__is_active=True
            ).exists()
        ):
            raise serializers.ValidationError({"shop": ["This shop is not available."]})
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        with transaction.atomic():
            from accounts.models import User

            User.objects.select_for_update().get(pk=user.pk)
            duplicate = Report.objects.filter(
                reporter=user,
                listing=validated_data.get("listing"),
                shop=validated_data.get("shop"),
                reason=validated_data["reason"],
                status__in=("open", "reviewing"),
            ).first()
            if duplicate:
                return duplicate
            return Report.objects.create(reporter=user, **validated_data)


class ReportDecisionSerializer(serializers.ModelSerializer):
    action = serializers.ChoiceField(
        choices=("review", "dismiss", "resolve", "hide_listing", "suspend_shop")
    )
    reason = serializers.CharField(max_length=2000)
    response = serializers.CharField(max_length=500)

    class Meta:
        model = Report
        fields = ("version", "action", "reason", "response")
        extra_kwargs: ClassVar[dict] = {"version": {"required": True, "min_value": 1}}


class ReportAuditSerializer(serializers.ModelSerializer):
    actor_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = ReportDecision
        fields = ("id", "actor_id", "action", "reason", "created_at")
