from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from authentication.models import StaffAccount

class StaffAccountAdmin(UserAdmin):
    list_display = ('center_detail', 'first_name', 'last_name', 'phone_number', 'address', 'username', 'email', 'is_locked')
    ordering = ['center_detail']
    fieldsets = (
        ('Personal Info', {
            'fields': ('username', 'center_detail', 'email', 'first_name', 'last_name', 'phone_number', 'address', "password")
        }),
        ('Permissions', {
            'fields': ('is_admin', 'is_staff', 'is_superuser', 'is_locked')
        }),
    )

admin.site.register(StaffAccount, StaffAccountAdmin)