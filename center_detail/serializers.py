from rest_framework import serializers
from .models import CenterDetail, Subscription
from datetime import date

from rest_framework import serializers
from datetime import date
from .models import CenterDetail, Subscription

from rest_framework import serializers
from .models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    center_name = serializers.CharField(source="center.center_name", read_only=True)
    days_left = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id",
            "center",
            "center_name",
            "plan_type",
            "purchase_date",
            "expiry_date",
            "is_active",
            "days_left",
        ]
        extra_kwargs = {
            "purchase_date": {"required": True},
            "expiry_date": {"required": True},
            "plan_type": {"required": True},
            "center": {"required": True},
        }

    def get_days_left(self, obj):
        return obj.days_left

    def create(self, validated_data):
        center = validated_data["center"]
        instance = Subscription.objects.filter(center=center).first()
        if instance:
            # Update all fields including is_active
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        return Subscription.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # Update all fields including is_active
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class CenterDetailListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer (no subscription info)."""
    class Meta:
        model = CenterDetail
        fields = ["id", "center_name", "address", "owner_name", "owner_phone"]


class CenterDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with subscription info for superusers only."""
    subscription = serializers.SerializerMethodField()

    class Meta:
        model = CenterDetail
        fields = ["id", "center_name", "address", "owner_name", "owner_phone", "subscription"]

    def get_subscription(self, obj):
        subscription = obj.subscriptions.order_by("-expiry_date").first()
        if subscription:
            return SubscriptionSerializer(subscription).data
        return None
class MinimalCenterDetailSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for dropdowns, lists, or foreign key fields.
    Does NOT include subscription info.
    """
    class Meta:
        model = CenterDetail
        fields = ["id", "center_name", "address"]

class CenterDetailTokenSerializer(serializers.ModelSerializer):
    subscription = serializers.SerializerMethodField()

    class Meta:
        model = CenterDetail
        fields = [
            "id",
            "center_name",
            "address",
            "owner_name",
            "owner_phone",
            "subscription",
        ]

    def get_subscription(self, obj):
        subscription = obj.subscriptions.order_by("-expiry_date").first()
        if subscription:
            return SubscriptionSerializer(subscription).data
        return None
