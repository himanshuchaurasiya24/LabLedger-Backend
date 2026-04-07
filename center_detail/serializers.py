from rest_framework import serializers

from .models import CenterDetail, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "duration_days",
            "price_monthly",
            "bulk_price",
            "monthly_sms_quota",
            "bulk_sms_quota",
            "is_custom",
            "is_active",
        ]


class CenterDetailListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer (no subscription info)."""
    is_active = serializers.BooleanField(source="subscription_is_active", read_only=True)

    class Meta:
        model = CenterDetail
        fields = ["id", "center_name", "address", "owner_name", "owner_phone", "is_active"]


class CenterDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with subscription plan."""
    is_active = serializers.BooleanField(source="subscription_is_active", read_only=True)
    active_state = serializers.BooleanField(source="is_active", write_only=True, required=False)
    subscription_plan = serializers.SerializerMethodField()
    subscription_plan_id = serializers.PrimaryKeyRelatedField(
        source="subscription_plan",
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = CenterDetail
        fields = [
            "id",
            "center_name",
            "address",
            "owner_name",
            "owner_phone",
            "is_active",
            "active_state",
            "subscription_plan",
            "subscription_plan_id",
        ]

    def get_subscription_plan(self, obj):
        plan = obj.subscription_plan
        if not plan:
            return None

        data = SubscriptionPlanSerializer(plan).data
        data.update({
            "purchase_date": obj.plan_activated_on.isoformat() if obj.plan_activated_on else None,
            "expiry_date": obj.subscription_expiry_date.isoformat() if obj.subscription_expiry_date else None,
            "days_left": obj.subscription_days_left,
            "is_active": obj.subscription_is_active,
        })
        return data

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if not (request and request.user.is_superuser):
            validated_data.pop("is_active", None)
        return super().update(instance, validated_data)

    def create(self, validated_data):
        request = self.context.get("request")
        if not (request and request.user.is_superuser):
            validated_data.pop("is_active", None)
        return super().create(validated_data)


class MinimalCenterDetailSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for dropdowns, lists, or foreign key fields.
    Does NOT include subscription info.
    """
    class Meta:
        model = CenterDetail
        fields = ["id", "center_name", "address"]

class CenterDetailTokenSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(source="subscription_is_active", read_only=True)
    subscription_plan = serializers.SerializerMethodField()

    class Meta:
        model = CenterDetail
        fields = [
            "id",
            "center_name",
            "address",
            "owner_name",
            "owner_phone",
            "is_active",
            "subscription_plan",
        ]

    def get_subscription_plan(self, obj):
        plan = obj.subscription_plan
        if not plan:
            return None

        data = SubscriptionPlanSerializer(plan).data
        data.update({
            "purchase_date": obj.plan_activated_on.isoformat() if obj.plan_activated_on else None,
            "expiry_date": obj.subscription_expiry_date.isoformat() if obj.subscription_expiry_date else None,
            "days_left": obj.subscription_days_left,
            "is_active": obj.subscription_is_active,
        })
        return data
