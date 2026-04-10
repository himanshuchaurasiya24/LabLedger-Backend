from rest_framework import serializers
from datetime import date, timedelta

from .models import ActiveSubscription, CenterDetail, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    display_price = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "plan_index",
            "price",
            "duration_days",
            "sms_quota",
            "server_report_storage_quota_mb",
            "patient_report_storage_quota_mb",
            "is_custom",
            "display_price",
        ]

    def get_display_price(self, obj):
        if obj.name.upper() == "FREE":
            return "0"
        return "Contact us"


class CenterDetailListSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(source="subscription_is_active", read_only=True)

    class Meta:
        model = CenterDetail
        fields = ["id", "center_name", "address", "owner_name", "owner_phone", "is_active"]


class ActiveSubscriptionSerializer(serializers.ModelSerializer):
    subscription_plan = SubscriptionPlanSerializer(read_only=True)
    center_detail_id = serializers.PrimaryKeyRelatedField(
        source="center_detail",
        queryset=CenterDetail.objects.all(),
        write_only=True,
    )
    subscription_plan_id = serializers.PrimaryKeyRelatedField(
        source="subscription_plan",
        queryset=SubscriptionPlan.objects.all(),
        write_only=True,
    )

    class Meta:
        model = ActiveSubscription
        fields = [
            "id",
            "center_detail",
            "center_detail_id",
            "subscription_plan",
            "subscription_plan_id",
            "plan_activated_on",
            "plan_expires_on",
        ]
        read_only_fields = ["center_detail", "subscription_plan"]

    def create(self, validated_data):
        center = validated_data["center_detail"]
        plan = validated_data["subscription_plan"]
        manual_expiry_provided = "plan_expires_on" in validated_data

        existing = ActiveSubscription.objects.filter(center_detail=center).first()

        if not manual_expiry_provided:
            if existing and existing.plan_expires_on:
                base_date = max(existing.plan_expires_on, date.today())
            else:
                base_date = validated_data.get("plan_activated_on") or date.today()
            validated_data["plan_expires_on"] = base_date + timedelta(
                days=plan.duration_days
            )

        # If one already exists for the center, treat create as reassignment update.
        if existing:
            for key, value in validated_data.items():
                setattr(existing, key, value)
            existing.save()
            return existing

        return super().create(validated_data)

    def update(self, instance, validated_data):
        plan = validated_data.get("subscription_plan", instance.subscription_plan)
        manual_expiry_provided = "plan_expires_on" in validated_data
        plan_changed = (
            "subscription_plan" in validated_data
            and validated_data["subscription_plan"].id != instance.subscription_plan_id
        )

        if plan_changed and not manual_expiry_provided:
            base_date = max(instance.plan_expires_on, date.today())
            validated_data["plan_expires_on"] = base_date + timedelta(
                days=plan.duration_days
            )
        elif "plan_activated_on" in validated_data and not manual_expiry_provided:
            validated_data["plan_expires_on"] = validated_data["plan_activated_on"] + timedelta(
                days=plan.duration_days
            )

        return super().update(instance, validated_data)


class CenterDetailSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(source="subscription_is_active", read_only=True)
    active_state = serializers.BooleanField(source="is_active", write_only=True, required=False)
    subscription_plan = serializers.SerializerMethodField()
    active_subscription = ActiveSubscriptionSerializer(read_only=True)

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
            "active_subscription",
        ]

    def get_subscription_plan(self, obj):
        plan = obj.subscription_plan
        if not plan:
            return None

        data = SubscriptionPlanSerializer(plan).data
        data.update(
            {
                "purchase_date": obj.plan_activated_on.isoformat() if obj.plan_activated_on else None,
                "expiry_date": obj.subscription_expiry_date.isoformat() if obj.subscription_expiry_date else None,
                "days_left": obj.subscription_days_left,
                "is_active": obj.subscription_is_active,
            }
        )
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
        data.update(
            {
                "purchase_date": obj.plan_activated_on.isoformat() if obj.plan_activated_on else None,
                "expiry_date": obj.subscription_expiry_date.isoformat() if obj.subscription_expiry_date else None,
                "days_left": obj.subscription_days_left,
                "is_active": obj.subscription_is_active,
            }
        )
        return data
