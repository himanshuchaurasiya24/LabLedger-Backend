from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User
from .models import StaffAccount
from .admin_mixins import CenterFilteredAdminMixin

# --- Define the Custom Admin Site ---
class CustomAdminSite(AdminSite):
    def has_permission(self, request):
        return request.user.is_active and request.user.is_staff

# --- Create a single instance of your custom site ---
custom_admin_site = CustomAdminSite(name='custom_admin')

# --- Define the ModelAdmin for your custom user ---
class StaffAccountAdmin(CenterFilteredAdminMixin, UserAdmin):
    list_display = ('username', 'center_detail', 'first_name', 'last_name', 'email', 'is_admin', 'is_superuser')
    ordering = ['center_detail', 'username']
    list_filter = ('is_superuser', 'is_admin', 'is_locked', 'center_detail')
    
    # Customizing the fieldsets to show 'is_admin' instead of 'is_staff'
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_admin', 'is_superuser', 'groups', 'user_permissions')}),
        ('Center Info & Status', {'fields': ('center_detail', 'phone_number', 'address', 'is_locked')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Required Info', {'fields': ('center_detail', 'first_name', 'last_name', 'email', 'phone_number', 'address')}),
    )

# --- Register/Unregister models on YOUR custom site ---
custom_admin_site.register(StaffAccount, StaffAccountAdmin)
try:
    custom_admin_site.unregister(User)
    custom_admin_site.unregister(Group)
except admin.sites.NotRegistered:
    pass