from django.contrib import admin

from diagnosis.models import *

class DoctorAdmin(admin.ModelAdmin):
    list_display= ('first_name','last_name','phone_number','address')
    ordering = ['first_name']
class BillAdmin(admin.ModelAdmin):
    list_display= ('bill_number','patient_name','date_of_test','total_amount','bill_status')
    ordering = ['bill_number']
admin.site.register(Doctor,DoctorAdmin)
admin.site.register(DiagnosisType)
admin.site.register(Bill, BillAdmin)
admin.site.register(Report)

