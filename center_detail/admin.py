from django.contrib import admin

from authentication.admin import custom_admin_site
from authentication.admin_mixins import CenterFilteredAdminMixin
from .models import ActiveSubscription, CenterDetail, SubscriptionPlan

class CenterDetailAdmin(CenterFilteredAdminMixin, admin.ModelAdmin):
    list_display = (
        "center_name",
        "address",
        "owner_name",
        "owner_phone",
        "subscription_status",
        "subscription_plan",
    )
    search_fields = ("center_name", "owner_name")
    list_select_related = ("active_subscription__subscription_plan",)

    def get_queryset(self, request):
        qs = super(CenterFilteredAdminMixin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs.select_related("active_subscription__subscription_plan")
        if hasattr(request.user, 'center_detail') and request.user.center_detail:
            return qs.filter(pk=request.user.center_detail.pk).select_related("active_subscription__subscription_plan")
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

    def subscription_plan(self, obj):
        plan = obj.subscription_plan
        return plan.name if plan else "-"

    subscription_plan.short_description = "Subscription Plan"

class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "duration_days",
        "sms_quota",
        "server_report_storage_quota_mb",
        "patient_report_storage_quota_mb",
        "is_custom",
    )
    list_filter = ("is_custom",)
    search_fields = ("name",)


class ActiveSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "center_detail",
        "subscription_plan",
        "plan_activated_on",
        "plan_expires_on",
    )
    search_fields = ("center_detail__center_name", "subscription_plan__name")
    list_select_related = ("center_detail", "subscription_plan")

# --- Register models on the custom site ---
custom_admin_site.register(CenterDetail, CenterDetailAdmin)
custom_admin_site.register(SubscriptionPlan, SubscriptionPlanAdmin)
custom_admin_site.register(ActiveSubscription, ActiveSubscriptionAdmin)