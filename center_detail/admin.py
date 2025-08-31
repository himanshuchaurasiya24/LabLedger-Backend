from django.contrib import admin
from .models import CenterDetail, Subscription


class SubscriptionInline(admin.TabularInline):
    """
    Inline subscription section inside Center admin.
    Shows latest subscription info (read-only by default).
    """
    model = Subscription
    extra = 0
    fields = ("plan_type", "purchase_date", "valid_days", "valid_till", "days_left", "is_active")
    readonly_fields = ("purchase_date", "valid_till", "days_left", "is_active")

    def has_add_permission(self, request, obj=None):
        # Only superusers can add subscription
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        # Only superusers can change subscription
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete subscription
        return request.user.is_superuser


@admin.register(CenterDetail)
class CenterDetailAdmin(admin.ModelAdmin):
    list_display = ("center_name", "address", "owner_name", "owner_phone", "get_current_plan", "get_days_left")
    search_fields = ("center_name", "address", "owner_name", "owner_phone")
    inlines = [SubscriptionInline]

    def get_current_plan(self, obj):
        sub = obj.current_subscription
        return sub.plan_type if sub else "No Subscription"
    get_current_plan.short_description = "Current Plan"

    def get_days_left(self, obj):
        sub = obj.current_subscription
        return sub.days_left if sub else "-"
    get_days_left.short_description = "Days Left"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("center", "plan_type", "purchase_date", "valid_till", "days_left", "is_active")
    list_filter = ("plan_type", "is_active")
    search_fields = ("center__center_name", "center__owner_name")
    readonly_fields = ("purchase_date", "valid_till", "days_left", "is_active")

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
