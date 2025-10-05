import os
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from authentication.serializers import MinimalStaffAccountSerializer
from center_detail.serializers import MinimalCenterDetailSerializer
from .models import Bill, DiagnosisType, Doctor, FranchiseName, PatientReport, SampleTestReport

class MinimalDiagnosisTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosisType
        fields = ['id', 'name', 'category', 'price']

class MinimalBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = ['id', 'bill_number', 'patient_name', 'patient_age', 'patient_sex']
class MinimalBillSerializerForPendingReports(serializers.ModelSerializer):
    diagnosis_type= MinimalDiagnosisTypeSerializer(serializers.ModelSerializer)
    class Meta:
        model = Bill
        fields = ['id',  'patient_name', 'patient_age', 'patient_sex', 'diagnosis_type', 'date_of_bill', 'referred_by_doctor']

class MinimalDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'first_name', 'last_name', 'address', 'email']


# --- Main Model Serializers (Refactored) ---
class DiagnosisTypeSerializer(serializers.ModelSerializer):
    # center_detail = MinimalCenterDetailSerializer(read_only=True)

    class Meta:
        model = DiagnosisType
        fields = ['id', 'name', 'category','price']
        read_only_fields = ['center_detail']

    def validate(self, attrs):
        """
        Manually check for the uniqueness of 'name' within the user's center.
        """
        user_center = self.context['request'].user.center_detail
        name = attrs.get('name')

        # Build a queryset to check for existing names in the same center.
        queryset = DiagnosisType.objects.filter(
            name=name,
            center_detail=user_center
        )

        # If we are updating an existing instance, exclude it from the check.
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        # If any other diagnosis type with this name exists, raise an error.
        if queryset.exists():
            raise serializers.ValidationError({
                'name': 'This diagnosis type already exists in your center.'
            })
            
        return attrs
class DoctorSerializer(serializers.ModelSerializer):
    # center_detail = MinimalCenterDetailSerializer(read_only=True)

    class Meta:
        model = Doctor
        fields = [
            'id', 
            'first_name', 
            'last_name', 
            'hospital_name', 
            'address', 
            'phone_number', 
            'email', 
            'ultrasound_percentage', 
            'pathology_percentage', 
            'ecg_percentage', 
            'xray_percentage', 
            'franchise_lab_percentage'
        ]
        read_only_fields = ['id', 'center_detail']

    def validate(self, attrs):
        """
        Check for uniqueness of phone_number within the user's center.
        """
        # Get the user's center from the request context provided by the ViewSet.
        user_center = self.context['request'].user.center_detail
        phone_number = attrs.get('phone_number')

        # Build the queryset to check for duplicates.
        queryset = Doctor.objects.filter(
            phone_number=phone_number, 
            center_detail=user_center
        )

        # On update (self.instance is available), exclude the current doctor
        # from the check to allow saving without changing the phone number.
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        # If any other doctor with this phone number exists in the center, raise an error.
        if queryset.exists():
            raise serializers.ValidationError({
                'phone_number': 'A doctor with this phone number already exists in your center.'
            })
            
        return attrs

class FranchiseNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = FranchiseName
        fields = ['id', 'franchise_name', 'address', 'phone_number'
        #  'center_detail'
         ]
        read_only_fields = ('center_detail',)

    def validate(self, attrs):
        """
        Manually check for uniqueness of franchise_name within the user's center.
        """
        # Get the user's center from the request context.
        user_center = self.context['request'].user.center_detail
        franchise_name = attrs.get('franchise_name')

        # Build the queryset to check for duplicates.
        queryset = FranchiseName.objects.filter(
            franchise_name=franchise_name,
            center_detail=user_center
        )

        # On update, exclude the current instance from the check.
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        # If any other franchise with this name exists in the center, raise an error.
        if queryset.exists():
            raise serializers.ValidationError({
                'franchise_name': 'This franchise name already exists in your center.'
            })
            
        return attrs

class BillSerializer(serializers.ModelSerializer):
    # --- Write-Only Fields (for input) ---
    diagnosis_type = serializers.PrimaryKeyRelatedField(
        queryset=DiagnosisType.objects.all(),
        write_only=True
    )
    referred_by_doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(),
        write_only=True
    )
    franchise_name = serializers.PrimaryKeyRelatedField(
        queryset=FranchiseName.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )
    diagnosis_type_output = MinimalDiagnosisTypeSerializer(source="diagnosis_type", read_only=True)
    referred_by_doctor_output = MinimalDoctorSerializer(source="referred_by_doctor", read_only=True)
    franchise_name_output = FranchiseNameSerializer(source='franchise_name', read_only=True)
    test_done_by = MinimalStaffAccountSerializer(read_only=True)
    center_detail = MinimalCenterDetailSerializer(read_only=True)
    match_reason = serializers.SerializerMethodField(read_only=True)
    report_url = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = [
            'id', 'bill_number', 'date_of_test', 'patient_name', 'patient_age',
            'patient_sex', 'date_of_bill', 'bill_status', 'total_amount',
            'paid_amount', 'disc_by_center', 'disc_by_doctor', 'incentive_amount',
            'diagnosis_type', 'referred_by_doctor', 'franchise_name',
            'diagnosis_type_output', 'referred_by_doctor_output', 'franchise_name_output',
            'test_done_by', 'center_detail', 'match_reason',"patient_phone_number","report_url"
        ]
        read_only_fields = (
            "bill_number", "test_done_by", "center_detail",
            "incentive_amount", "total_amount",
        )
    def get_report_url(self, bill):
        report = bill.report.first()
        if report and report.report_file:
            request = self.context.get("request")
            return request.build_absolute_uri(report.report_file.url)
        return None


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request.user, 'center_detail'):
            user_center = request.user.center_detail
            self.fields['diagnosis_type'].queryset = DiagnosisType.objects.filter(center_detail=user_center)
            self.fields['referred_by_doctor'].queryset = Doctor.objects.filter(center_detail=user_center)
            self.fields['franchise_name'].queryset = FranchiseName.objects.filter(center_detail=user_center)

    def get_match_reason(self, obj):
        return None

    def validate(self, attrs):
        user = self.context['request'].user
        if 'diagnosis_type' in attrs:
            final_diagnosis_type = attrs.get('diagnosis_type')
        elif self.instance:
            final_diagnosis_type = self.instance.diagnosis_type
        else:
            final_diagnosis_type = None
        if final_diagnosis_type and final_diagnosis_type.category != 'Franchise Lab':
            attrs['franchise_name'] = None
        attrs['center_detail'] = user.center_detail
        attrs['test_done_by'] = user
        instance = self.instance or Bill()
        for attr, value in attrs.items():
            setattr(instance, attr, value)

        try:
            instance.full_clean()
        except DjangoValidationError as e:
            raise DRFValidationError(e.message_dict)

        # Remove temporary keys before the serializer saves the data
        attrs.pop('center_detail')
        attrs.pop('test_done_by')

        return attrs
class IncentiveDiagnosisTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosisType
        fields = [ 'name', 'category', 'price']
class IncentiveFranchiseNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = FranchiseName
        fields= ['franchise_name']
class IncentiveDoctorSerializer (serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields=['id', 'first_name','last_name','hospital_name', 'ultrasound_percentage', 'pathology_percentage', 'ecg_percentage', 'xray_percentage', 'franchise_lab_percentage']
class IncentiveBillSerializer(serializers.ModelSerializer):
    """
    A read-only serializer for displaying nested bill details in reports.
    """
    diagnosis_type = IncentiveDiagnosisTypeSerializer( read_only=True)
    franchise_name = IncentiveFranchiseNameSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Bill
        fields = [
            'id',
            'bill_number',
            'patient_name',
            'patient_age',
            'patient_sex',
            'patient_phone_number', 
            'diagnosis_type',
            'franchise_name',
            'date_of_bill',
            'bill_status',
            'total_amount',
            'paid_amount',
            'disc_by_doctor',       
            'disc_by_center',       
            'incentive_amount'
        ]
        



class PatientReportSerializer(serializers.ModelSerializer):
    bill_output = MinimalBillSerializer(read_only=True, source='bill')
    bill = serializers.PrimaryKeyRelatedField(queryset=Bill.objects.all(), write_only=True)

    class Meta:
        model = PatientReport
        fields = ['id', 'report_file', "bill", "bill_output"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request.user, 'center_detail'):
            user_center = request.user.center_detail
            self.fields['bill'].queryset = Bill.objects.filter(center_detail=user_center)

class SampleTestReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleTestReport
        fields = ['id', 'category', 'diagnosis_name', 'sample_report_file']

    def validate_sample_report_file(self, value):
        """
        Custom validation for the uploaded file.
        This is the correct place for validation in DRF.
        """
        file_size_limit = 8 * 1024 * 1024  # 8 MB
        allowed_formats = ('.doc', '.docx', '.rtf')
        if value.size > file_size_limit:
            raise serializers.ValidationError(f"File size cannot exceed 8 MB.")
        
        file_extension = os.path.splitext(value.name)[1].lower()
        if file_extension not in allowed_formats:
            raise serializers.ValidationError(
                f"Invalid file format. Only Word documents ({', '.join(allowed_formats)}) are allowed."
            )
        return value