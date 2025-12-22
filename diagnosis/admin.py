from django.contrib import admin
from authentication.admin import custom_admin_site
from authentication.admin_mixins import CenterFilteredAdminMixin
from .models import (
    Doctor,
    Bill,
    DiagnosisType,
    PatientReport,
    SampleTestReport,
    FranchiseName,
    DiagnosisCategory,
    DoctorCategoryPercentage,
)

# A generic admin class that includes our filtering for simple models
class FilteredBaseAdmin(CenterFilteredAdminMixin, admin.ModelAdmin):
    """A base ModelAdmin for simple models that just need center filtering."""
    pass


# ModelAdmin for Doctor (Uses the mixin)
class DoctorAdmin(CenterFilteredAdminMixin, admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone_number', 'address', 'center_detail')
    ordering = ['first_name']
    search_fields = ('first_name', 'last_name')


# ModelAdmin for Bill (Uses the mixin)
class BillAdmin(CenterFilteredAdminMixin, admin.ModelAdmin):
    list_display = (
        'bill_number',
        'patient_name',
        'total_amount',
        'referred_by_doctor',
        'test_done_by',
        'date_of_test',
        'center_detail'
    )
    readonly_fields = ('bill_number', 'total_amount', 'incentive_amount')
    list_filter = ('date_of_test', 'center_detail', 'test_done_by')
    ordering = ['-date_of_test']


# Register all models on the custom admin site

# Register the models that have their own custom admin classes
custom_admin_site.register(Doctor, DoctorAdmin)
custom_admin_site.register(Bill, BillAdmin)

# Register the rest of the models using our new generic filtered admin class
custom_admin_site.register(DiagnosisType, FilteredBaseAdmin)
custom_admin_site.register(PatientReport, FilteredBaseAdmin)
custom_admin_site.register(SampleTestReport, FilteredBaseAdmin)
custom_admin_site.register(FranchiseName, FilteredBaseAdmin)
custom_admin_site.register(DiagnosisCategory)
custom_admin_site.register(DoctorCategoryPercentage)