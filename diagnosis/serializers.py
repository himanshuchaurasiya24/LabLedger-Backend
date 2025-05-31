from center_detail.serializers import CenterDetailSerializer
from .models import *
from rest_framework import serializers
from .models import *

class DiagnosisTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosisType
        fields = '__all__'
class StaffAccountSerializer(serializers.ModelSerializer):    
    class Meta:
        model = StaffAccount
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'address']
class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'first_name', 'last_name', 'address', 'phone_number', 'ultrasound_percentage', 'pathology_percentage', 'ecg_percentage', 'xray_percentage']
class BillSerializer(serializers.ModelSerializer):
    diagnosis_type = DiagnosisTypeSerializer(read_only=True)
    test_done_by = StaffAccountSerializer(read_only=True)
    referred_by_doctor = DoctorSerializer(read_only=True)
    center_detail = CenterDetailSerializer(read_only=True)
    class Meta:
        model = Bill
        # All fields you want to expose:
        fields = '__all__'
        # Make these read-only:
        read_only_fields = (
            'bill_number',
            'total_amount',
            'incentive_amount',
        )
class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model= Report
        fields = '__all__'
   