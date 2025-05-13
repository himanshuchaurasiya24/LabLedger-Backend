from django.contrib import admin

from diagnosis.models import Bill, DiagnosisType, Doctor

class DoctorAdmin(admin.ModelAdmin):
    list_display= ('first_name','last_name','phone_number','address')
    ordering = ['first_name']
admin.site.register(Doctor,DoctorAdmin)
admin.site.register(DiagnosisType)
admin.site.register(Bill)
