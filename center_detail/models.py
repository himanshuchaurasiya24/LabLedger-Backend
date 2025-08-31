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
        is_new = self.pk is None  # check if this is a new center
        super().save(*args, **kwargs)

        # If it's a new center, create a FREE subscription by default
        if is_new:
            Subscription.objects.create(
                center=self,
                plan_type="FREE",
                valid_days=30,
            )


class Subscription(models.Model):
    PLAN_CHOICES = [
        ("FREE", "Free"),
        ("BASIC", "Basic"),
        ("PREMIUM", "Premium"),
    ]

    center = models.ForeignKey("CenterDetail", on_delete=models.CASCADE, related_name="subscriptions")
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES)
    purchase_date = models.DateField(auto_now_add=True)
    valid_days = models.PositiveIntegerField(default=30)
    valid_till = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    @property
    def days_left(self):
        if self.valid_till:
            return (self.valid_till - date.today()).days
        return None

    def save(self, *args, **kwargs):
        if not self.purchase_date:
            self.purchase_date = date.today()

        if self.valid_days:
            self.valid_till = self.purchase_date + timedelta(days=self.valid_days)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.center.center_name} - {self.plan_type}"
