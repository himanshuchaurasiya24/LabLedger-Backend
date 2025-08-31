from rest_framework import serializers
from django.utils import timezone

from center_detail.models import CenterDetail, Subscription  # ✅ use Django timezone, not datetime.timezone


class SubscriptionSerializer(serializers.ModelSerializer):
    center_name = serializers.CharField(source="center.center_name", read_only=True)
    days_left = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id",
            "center",
            "center_name",
            "plan_type",
            "purchase_date",
            "valid_days",
            "valid_till",
            "days_left",
            "is_active",
        ]

    def get_days_left(self, obj):
        if obj.valid_till:
            remaining = (obj.valid_till - timezone.now().date()).days
            return max(remaining, 0)
        return None

    def get_is_active(self, obj):
        return obj.valid_till and obj.valid_till >= timezone.now().date()
class MinimalCenterDetailSerializer(serializers.ModelSerializer):
    """Lightweight version for dropdowns, etc."""
    class Meta:
        model = CenterDetail
        fields = ["id", "center_name", "address"]


class CenterDetailListSerializer(serializers.ModelSerializer):
    """Serializer for list view (/centers/) without subscription info"""
    class Meta:
        model = CenterDetail
        fields = [
            "id",
            "center_name",
            "address",
            "owner_name",
            "owner_phone",
        ]


class CenterDetailSerializer(serializers.ModelSerializer):
    """Serializer for detail view (/centers/{id}/) with subscription info only for superuser"""
    current_subscription = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CenterDetail
        fields = [
            "id",
            "center_name",
            "address",
            "owner_name",
            "owner_phone",
            "current_subscription",  # 👈 shown only if user is superuser
        ]

    def get_current_subscription(self, obj):
        request = self.context.get("request")
        if request and request.user and request.user.is_superuser:
            # ✅ fetch latest subscription for this center
            subscription = obj.subscriptions.order_by("-purchase_date").first()
            return SubscriptionSerializer(subscription).data if subscription else None
        return None


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
        # fetch latest subscription for this center
        subscription = Subscription.objects.filter(center=obj).order_by("-id").first()
        if subscription:
            return SubscriptionSerializer(subscription).data
        return None