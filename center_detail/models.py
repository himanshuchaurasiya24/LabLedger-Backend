# center_detail/models.py

from django.db import models
from datetime import timedelta, date

class CenterDetail(models.Model):
    center_name = models.CharField(max_length=30)
    address = models.CharField(max_length=50)
    owner_name = models.CharField(max_length=30)
    owner_phone = models.CharField(max_length=15, unique=True)

    def __str__(self):
        return self.center_name

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Create default FREE subscription
            Subscription.objects.create(
                center=self,
                plan_type="FREE",
            )


class Subscription(models.Model):
    PLAN_CHOICES = [
        ("FREE", "Free"),
        ("BASIC", "Basic"),
        ("PREMIUM", "Premium"),
    ]

    center = models.ForeignKey(
        CenterDetail,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES)
    purchase_date = models.DateField()
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)

    @property
    def days_left(self):
        if not self.expiry_date:
            return 0
        remaining = (self.expiry_date - date.today()).days
        return max(remaining, 0)

    def save(self, *args, **kwargs):
        # Default dates if not provided
        if not self.purchase_date:
            self.purchase_date = date.today()
        if not self.expiry_date:
            if self.plan_type == "PREMIUM":
                self.expiry_date = self.purchase_date + timedelta(days=365)
            # This covers both "FREE" and "BASIC"
            else:
                self.expiry_date = self.purchase_date + timedelta(days=30)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.center.center_name} - {self.plan_type}"