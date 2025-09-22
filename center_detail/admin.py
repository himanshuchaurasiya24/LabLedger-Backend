from django.contrib import admin
from authentication.admin import custom_admin_site
from authentication.admin_mixins import CenterFilteredAdminMixin
from .models import CenterDetail, Subscription

# --- Inlines and Admin Classes ---
class SubscriptionInline(admin.TabularInline):
    model = Subscription
    extra = 0
    fields = ("plan_type", "purchase_date", "expiry_date", "days_left", "is_active")
    readonly_fields = ("purchase_date", "expiry_date", "days_left", "is_active")

class CenterDetailAdmin(CenterFilteredAdminMixin, admin.ModelAdmin):
    list_display = ("center_name", "address", "owner_name", "owner_phone", "get_plan", "get_days_left")
    search_fields = ("center_name", "owner_name")
    inlines = [SubscriptionInline]

    def get_queryset(self, request):
        qs = super(CenterFilteredAdminMixin, self).get_queryset(request)
        prefetch_name = 'subscriptions'
        if request.user.is_superuser:
            return qs.prefetch_related(prefetch_name)
        if hasattr(request.user, 'center_detail') and request.user.center_detail:
            return qs.filter(pk=request.user.center_detail.pk).prefetch_related(prefetch_name)
        return qs.none()

    # --- PERMISSION OVERRIDES ---
    def has_view_permission(self, request, obj=None):
        # Allows a user to see the list page and their own center's detail page.
        return True

    def has_change_permission(self, request, obj=None):
        # Superusers can change anything.
        if request.user.is_superuser:
            return True
        # A non-superuser can only change their own center.
        if obj is not None:
            return obj == request.user.center_detail
        return False

    def has_add_permission(self, request):
        # Only superusers can add new centers.
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete centers.
        return request.user.is_superuser

    # --- Custom display methods ---
    def get_plan(self, obj):
        latest_sub = obj.subscriptions.order_by('-purchase_date').first()
        return latest_sub.plan_type if latest_sub else "No Subscription"
    get_plan.short_description = "Current Plan"

    def get_days_left(self, obj):
        latest_sub = obj.subscriptions.order_by('-purchase_date').first()
        return latest_sub.days_left if latest_sub else "-"
    get_days_left.short_description = "Days Left"

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("center", "plan_type", "purchase_date", "expiry_date", "days_left", "is_active")
    list_filter = ("plan_type", "is_active")
    search_fields = ("center__center_name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'center_detail') and request.user.center_detail:
            return qs.filter(center=request.user.center_detail)
        return qs.none()

# --- Register models on the custom site ---
custom_admin_site.register(CenterDetail, CenterDetailAdmin)
custom_admin_site.register(Subscription, SubscriptionAdmin)