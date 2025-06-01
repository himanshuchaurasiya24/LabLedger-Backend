from center_detail.serializers import CenterDetailSerializer
from .models import *
from rest_framework import serializers
from .models import *

class DiagnosisTypeSerializer(serializers.ModelSerializer):
    center_detail = serializers.PrimaryKeyRelatedField(queryset= CenterDetail.objects.all(), write_only=True)
    center_detail_output = CenterDetailSerializer(read_only=True, source='center_detail')
    class Meta:
        model = DiagnosisType
        fields ='__all__'
class StaffAccountSerializer(serializers.ModelSerializer):    
    class Meta:
        model = StaffAccount
        fields = ['id',  'first_name', 'last_name']
class DoctorSerializer(serializers.ModelSerializer):
    center_detail = serializers.PrimaryKeyRelatedField(
        queryset=CenterDetail.objects.all(),
        write_only=True
    )
    center_detail_output = CenterDetailSerializer(read_only=True, source='center_detail')
    class Meta:
        model = Doctor
        fields = "__all__"
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
            'date_of_test',

        )
class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model= Report
        fields = '__all__'
   