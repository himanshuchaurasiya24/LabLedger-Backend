from django.core.exceptions import ValidationError
from django.contrib import admin
from diagnosis.models import *

class DoctorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone_number', 'address', 'center_detail')
    ordering = ['first_name']


class BillAdmin(admin.ModelAdmin):
    ordering = ['bill_number']
    list_display = ('bill_number', 'total_amount', 'incentive_amount', "referred_by_doctor", 'date_of_test','patient_name','test_done_by', 'center_detail')
    readonly_fields = ('bill_number', 'total_amount', 'incentive_amount')
# *******************DON'NT REMOVE THIS CODE 
# *******************IT IS USED FOR EDITIING 
# *******************THE AUTOMATICALLY SET FIELDS 
# *******************IN BILL MODEL ON THE ADMIN SITE____________________
    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     user_center = getattr(request.user, 'center_detail', None)

    #     if db_field.name == 'test_done_by':
    #         kwargs["queryset"] = Doctor.objects.filter(center_detail=user_center)
    #     elif db_field.name == 'referred_by_doctor':
    #         kwargs["queryset"] = Doctor.objects.filter(center_detail=user_center)
    #     elif db_field.name == 'diagnosis_type':
    #         kwargs["queryset"] = DiagnosisType.objects.filter(center_detail=user_center)

    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:
            # Pre-set center_detail and test_done_by for new bills
            form.base_fields['center_detail'].initial = request.user.center_detail
            form.base_fields['test_done_by'].initial = request.user
        return form

    def save_model(self, request, obj, form, change):
        if not change:
            obj.test_done_by = request.user
            obj.center_detail = request.user.center_detail

        if obj.test_done_by.center_detail != obj.center_detail:
            raise ValidationError("Doctor's center must match the bill's center.")

        if obj.referred_by_doctor and obj.referred_by_doctor.center_detail != obj.center_detail:
            raise ValidationError("Referred doctor's center must match the bill's center.")

        if obj.diagnosis_type and obj.diagnosis_type.center_detail != obj.center_detail:
            raise ValidationError("Diagnosis type's center must match the bill's center.")

        super().save_model(request, obj, form, change)


admin.site.register(Doctor, DoctorAdmin)
admin.site.register(DiagnosisType)
admin.site.register(Bill, BillAdmin)
admin.site.register(PatientReport)
admin.site.register(SampleTestReport)
admin.site.register(FranchiseName)
