from authentication.serializers import *
from center_detail.serializers import *
from .models import *
from rest_framework import serializers
from .models import *

class MinimalDiagnosisTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosisType
        fields = ['id', 'name', 'category', 'price']
class MinimalDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields= ['id','first_name', 'last_name', 'address']
class DiagnosisTypeSerializer(serializers.ModelSerializer):
    center_detail = serializers.PrimaryKeyRelatedField(queryset= CenterDetail.objects.all(), write_only=True)
    center_detail_output = MinimalCenterDetailSerializer(read_only=True, source='center_detail')
    class Meta:
        model = DiagnosisType
        fields ='__all__'


class DoctorSerializer(serializers.ModelSerializer):
    center_detail = serializers.PrimaryKeyRelatedField(queryset= CenterDetail.objects.all(), write_only=True)
    center_detail_output = MinimalCenterDetailSerializer(read_only=True, source='center_detail')
    class Meta:
        model = Doctor
        fields = "__all__"
        read_only_fields = ['id']


class BillSerializer(serializers.ModelSerializer):
    diagnosis_type = MinimalDiagnosisTypeSerializer(read_only=True)
    test_done_by = MinimalStaffAccountSerializer(read_only=True)
    referred_by_doctor = MinimalDoctorSerializer(read_only=True)
    center_detail = MinimalCenterDetailSerializer(read_only=True)
    class Meta:
        model = Bill
        fields = '__all__'
        read_only_fields = (
            'bill_number',
            'date_of_test',
            'test_done_by',
            'center_detail',
        )
class PatientReportSerializer(serializers.ModelSerializer):
    class Meta:
        model= PatientReport
        fields = '__all__'
   