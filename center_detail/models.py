from django.db import models
from datetime import date, timedelta


class SubscriptionPlan(models.Model):
    """Admin-managed subscription catalog for dynamic plans."""
    name = models.CharField(max_length=100, unique=True)
    duration_days = models.PositiveIntegerField(default=30)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bulk_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monthly_sms_quota = models.PositiveIntegerField(default=0)
    bulk_sms_quota = models.PositiveIntegerField(default=0)
    is_custom = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class CenterDetail(models.Model):
    center_name = models.CharField(max_length=30)
    address = models.CharField(max_length=50)
    owner_name = models.CharField(max_length=30)
    owner_phone = models.CharField(max_length=15, unique=True)
    is_active = models.BooleanField(default=True)
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="centers",
    )
    plan_activated_on = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.center_name

    def save(self, *args, **kwargs):
        previous_plan_id = None
        if self.pk:
            previous_plan_id = (
                CenterDetail.objects.filter(pk=self.pk)
                .values_list("subscription_plan_id", flat=True)
                .first()
            )

        if not self.subscription_plan:
            free_plan, _ = SubscriptionPlan.objects.get_or_create(
                name="FREE",
                defaults={
                    "duration_days": 30,
                    "price_monthly": 0,
                    "bulk_price": 0,
                    "monthly_sms_quota": 0,
                    "bulk_sms_quota": 0,
                    "is_custom": False,
                    "is_active": True,
                },
            )
            self.subscription_plan = free_plan

        if previous_plan_id != self.subscription_plan_id:
            self.plan_activated_on = date.today()
        elif self.subscription_plan_id and not self.plan_activated_on:
            self.plan_activated_on = date.today()

        if self.plan_activated_on and self.subscription_plan:
            expiry_date = self.plan_activated_on + timedelta(days=self.subscription_plan.duration_days)
            if expiry_date <= date.today():
                self.is_active = False

        super().save(*args, **kwargs)

    @property
    def subscription_expiry_date(self):
        if not self.subscription_plan or not self.plan_activated_on:
            return None
        return self.plan_activated_on + timedelta(days=self.subscription_plan.duration_days)

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