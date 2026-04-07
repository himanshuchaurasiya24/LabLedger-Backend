from django.contrib import admin

from authentication.admin import custom_admin_site
from authentication.admin_mixins import CenterFilteredAdminMixin
from .models import CenterDetail, SubscriptionPlan

class CenterDetailAdmin(CenterFilteredAdminMixin, admin.ModelAdmin):
    list_display = ("center_name", "address", "owner_name", "owner_phone", "subscription_status", "subscription_plan")
    search_fields = ("center_name", "owner_name")
    list_select_related = ("subscription_plan",)

    def get_queryset(self, request):
        qs = super(CenterFilteredAdminMixin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs.select_related("subscription_plan")
        if hasattr(request.user, 'center_detail') and request.user.center_detail:
            return qs.filter(pk=request.user.center_detail.pk).select_related("subscription_plan")
        return qs.none()

    # --- PERMISSION OVERRIDES ---
    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is not None:
            return obj == request.user.center_detail
        return False

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()
        return ("is_active",)

    def subscription_status(self, obj):
        return obj.subscription_is_active

    subscription_status.short_description = "Active"

class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "duration_days",
        "price_monthly",
        "bulk_price",
        "monthly_sms_quota",
        "bulk_sms_quota",
        "is_custom",
        "is_active",
    )
    list_filter = ("is_custom", "is_active")
    search_fields = ("name",)

# --- Register models on the custom site ---
custom_admin_site.register(CenterDetail, CenterDetailAdmin)
custom_admin_site.register(SubscriptionPlan, SubscriptionPlanAdmin)