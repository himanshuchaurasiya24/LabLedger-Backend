from django.db import models
from datetime import date, timedelta


class SubscriptionPlan(models.Model):
    """Master subscription plan template."""

    name = models.CharField(max_length=100, unique=True)
    plan_index = models.PositiveIntegerField(default=0, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_days = models.PositiveIntegerField(default=30)
    sms_quota = models.PositiveIntegerField(default=0)
    server_report_storage_quota_mb = models.PositiveIntegerField(default=0)
    patient_report_storage_quota_mb = models.PositiveIntegerField(default=0)
    is_custom = models.BooleanField(default=False)

    class Meta:
        ordering = ["plan_index", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.name.upper() == "FREE":
            self.plan_index = 0
        elif self.plan_index == 0 and not self.pk:
            highest_index = (
                SubscriptionPlan.objects.exclude(name__iexact="FREE")
                .aggregate(models.Max("plan_index"))["plan_index__max"]
                or 0
            )
            self.plan_index = highest_index + 1
        super().save(*args, **kwargs)


def get_free_plan():
    free_plan, _ = SubscriptionPlan.objects.get_or_create(
        name="FREE",
        defaults={
            "plan_index": 0,
            "price": 0,
            "duration_days": 30,
            "sms_quota": 0,
            "server_report_storage_quota_mb": 0,
            "patient_report_storage_quota_mb": 0,
            "is_custom": False,
        },
    )
    return free_plan


class ActiveSubscription(models.Model):
    center_detail = models.OneToOneField(
        "CenterDetail",
        on_delete=models.CASCADE,
        related_name="active_subscription",
    )
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.DO_NOTHING,
        related_name="active_subscriptions",
    )
    plan_activated_on = models.DateField(default=date.today)
    plan_expires_on = models.DateField()

    class Meta:
        ordering = ["-plan_expires_on", "-id"]

    def __str__(self):
        return f"{self.center_detail.center_name} - {self.subscription_plan.name}"

    def save(self, *args, **kwargs):
        if not self.plan_activated_on:
            self.plan_activated_on = date.today()

        previous = None
        if self.pk:
            previous = ActiveSubscription.objects.filter(pk=self.pk).first()

        # If plan changes and expiry was not manually changed, carry forward from
        # the current expiry date (or today if already expired), then add duration.
        if (
            previous
            and previous.subscription_plan_id != self.subscription_plan_id
            and self.plan_expires_on == previous.plan_expires_on
        ):
            base_date = max(previous.plan_expires_on, date.today())
            self.plan_expires_on = base_date + timedelta(
                days=self.subscription_plan.duration_days
            )

        # For first-time save or blank expiry, derive from activation date.
        if not self.plan_expires_on:
            self.plan_expires_on = self.plan_activated_on + timedelta(
                days=self.subscription_plan.duration_days
            )

        super().save(*args, **kwargs)

class CenterDetail(models.Model):
    center_name = models.CharField(max_length=30)
    address = models.CharField(max_length=50)
    owner_name = models.CharField(max_length=30)
    owner_phone = models.CharField(max_length=15, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.center_name

    @property
    def subscription_plan(self):
        active_sub = getattr(self, "active_subscription", None)
        return active_sub.subscription_plan if active_sub else None

    @property
    def plan_activated_on(self):
        active_sub = getattr(self, "active_subscription", None)
        return active_sub.plan_activated_on if active_sub else None

    @property
    def subscription_expiry_date(self):
        active_sub = getattr(self, "active_subscription", None)
        if not active_sub:
            return None
        return active_sub.plan_expires_on

    @property
    def subscription_days_left(self):
        expiry_date = self.subscription_expiry_date
        if not expiry_date:
            return 0
        return max((expiry_date - date.today()).days, 0)

    @property
    def subscription_is_active(self):
        if not self.is_active:
            return False
        if not self.subscription_plan:
            return False
        return self.subscription_days_left > 0