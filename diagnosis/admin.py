from django.contrib import admin

from diagnosis.models import *

class DoctorAdmin(admin.ModelAdmin):
    list_display= ('first_name','last_name','phone_number','address')
    ordering = ['first_name']
class BillAdmin(admin.ModelAdmin):
    ordering = ['bill_number']
    readonly_fields = ('bill_number', 'total_amount', 'incentive_amount')
admin.site.register(Doctor,DoctorAdmin)
admin.site.register(DiagnosisType)
admin.site.register(Bill, BillAdmin)
admin.site.register(PatientReport)

