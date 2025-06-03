from django.contrib import admin

from diagnosis.models import *

class DoctorAdmin(admin.ModelAdmin):
    list_display= ('first_name','last_name','phone_number','address')
    ordering = ['first_name']
class BillAdmin(admin.ModelAdmin):
    ordering = ['bill_number']
    readonly_fields = ('bill_number', 'total_amount', 'incentive_amount')
    # exclude will not show these fields in the admin form
    # exclude = ('center_detail', 'test_done_by')
    # this will prefill the fields with the user center_detail and test_done_by
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:
            # Pre-set center_detail on form initialization
            form.base_fields['center_detail'].initial = request.user.center_detail
            form.base_fields['test_done_by'].initial = request.user
        return form
    # this is requried after exclude to set the fields autmatically
    def save_model(self, request, obj, form, change):
        if not change:
            obj.test_done_by = request.user
            obj.center_detail = request.user.center_detail
        super().save_model(request, obj, form, change)

    
admin.site.register(Doctor,DoctorAdmin)
admin.site.register(DiagnosisType)
admin.site.register(Bill, BillAdmin)
admin.site.register(PatientReport)

