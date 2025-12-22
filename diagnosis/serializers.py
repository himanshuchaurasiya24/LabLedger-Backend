import os
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from authentication.serializers import MinimalStaffAccountSerializer
from center_detail.serializers import MinimalCenterDetailSerializer
from .models import Bill, DiagnosisType, Doctor, FranchiseName, PatientReport, SampleTestReport, BillDiagnosisType, DiagnosisCategory, DoctorCategoryPercentage


# ========================
# DIAGNOSIS CATEGORY SERIALIZERS
# ========================

class DiagnosisCategorySerializer(serializers.ModelSerializer):
    """Serializer for diagnosis categories"""
    class Meta:
        model = DiagnosisCategory
        fields = ['id', 'name', 'description', 'is_franchise_lab', 'is_active']


class DoctorCategoryPercentageSerializer(serializers.ModelSerializer):
    """Serializer for doctor category percentages"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    percentage = serializers.IntegerField(required=False, default=0)
    
    class Meta:
        model = DoctorCategoryPercentage
        fields = ['id', 'category', 'category_name', 'percentage']


class MinimalDiagnosisTypeSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(read_only=True)  # Explicitly serialize as ID
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    
    class Meta:
        model = DiagnosisType
        fields = ['id', 'name', 'category', 'category_name', 'price']

class MinimalBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = ['id', 'bill_number', 'patient_name', 'patient_age', 'patient_sex']
class MinimalBillSerializerForPendingReports(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = ['id', 'patient_name', 'patient_age', 'patient_sex', 'date_of_bill', 'referred_by_doctor']

class MinimalDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'first_name', 'last_name', 'address', 'email', 'ultrasound_percentage', 'pathology_percentage', 'ecg_percentage', 'xray_percentage', 'franchise_lab_percentage', 'others_percentage']


# --- Main Model Serializers (Refactored) ---
class DiagnosisTypeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = DiagnosisType
        fields = ['id', 'name', 'category', 'category_name', 'price']
        read_only_fields = ['center_detail', 'category_name']

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
    category_percentages = DoctorCategoryPercentageSerializer(many=True, required=False)
    
    # Make old fields optional with default 0 for backward compatibility
    ultrasound_percentage = serializers.IntegerField(required=False, allow_null=True, default=0)
    pathology_percentage = serializers.IntegerField(required=False, allow_null=True, default=0)
    ecg_percentage = serializers.IntegerField(required=False, allow_null=True, default=0)
    xray_percentage = serializers.IntegerField(required=False, allow_null=True, default=0)
    franchise_lab_percentage = serializers.IntegerField(required=False, allow_null=True, default=0)
    others_percentage = serializers.IntegerField(required=False, allow_null=True, default=0)

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
            'franchise_lab_percentage',
            'others_percentage',
            'category_percentages',
        ]
        read_only_fields = ['id', 'center_detail']

    def create(self, validated_data):
        category_percentages_data = validated_data.pop('category_percentages', [])
        
        # Set defaults for old percentage fields if not provided
        validated_data.setdefault('ultrasound_percentage', 0)
        validated_data.setdefault('pathology_percentage', 0)
        validated_data.setdefault('ecg_percentage', 0)
        validated_data.setdefault('xray_percentage', 0)
        validated_data.setdefault('franchise_lab_percentage', 0)
        validated_data.setdefault('others_percentage', 0)
        
        doctor = Doctor.objects.create(**validated_data)
        
        # Create category percentages if provided
        for cat_perc_data in category_percentages_data:
            DoctorCategoryPercentage.objects.create(doctor=doctor, **cat_perc_data)
        
        return doctor
    
    def update(self, instance, validated_data):
        category_percentages_data = validated_data.pop('category_percentages', None)
        
        # Update doctor fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update category percentages if provided
        if category_percentages_data is not None:
            # Delete existing category percentages
            instance.category_percentages.all().delete()
            # Create new ones
            for cat_perc_data in category_percentages_data:
                DoctorCategoryPercentage.objects.create(doctor=instance, **cat_perc_data)
        
        return instance

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

class BillDiagnosisTypeSerializer(serializers.ModelSerializer):
    """Serializer for the junction model"""
    diagnosis_type_detail = MinimalDiagnosisTypeSerializer(source='diagnosis_type', read_only=True)
    
    class Meta:
        model = BillDiagnosisType
        fields = ['diagnosis_type', 'diagnosis_type_detail', 'price_at_time']

class BillSerializer(serializers.ModelSerializer):
    # --- Write-Only Fields (for input) ---
    diagnosis_types = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True,
        allow_empty=False
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
    
    # --- Read-Only Fields (for output) ---
    diagnosis_types_output = serializers.SerializerMethodField(read_only=True)
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
            'diagnosis_types', 'referred_by_doctor', 'franchise_name',
            'diagnosis_types_output', 'referred_by_doctor_output', 'franchise_name_output',
            'test_done_by', 'center_detail', 'match_reason', 'patient_phone_number', 'report_url'
        ]
        read_only_fields = (
            "bill_number", "test_done_by", "center_detail",
            "incentive_amount", "total_amount",
        )
    
    def get_diagnosis_types_output(self, bill):
        """Get all diagnosis types for this bill with their details"""
        bill_diagnosis_types = bill.bill_diagnosis_types.all()
        return BillDiagnosisTypeSerializer(bill_diagnosis_types, many=True).data
    
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
            self.fields['referred_by_doctor'].queryset = Doctor.objects.filter(center_detail=user_center)
            self.fields['franchise_name'].queryset = FranchiseName.objects.filter(center_detail=user_center)

    def get_match_reason(self, obj):
        return None

    def validate_diagnosis_types(self, value):
        """Validate that all diagnosis type IDs exist and belong to user's center"""
        if not value:
            raise serializers.ValidationError("At least one diagnosis type must be selected.")
        
        user_center = self.context['request'].user.center_detail
        diagnosis_types = DiagnosisType.objects.filter(
            id__in=value,
            center_detail=user_center
        )
        
        if diagnosis_types.count() != len(value):
            raise serializers.ValidationError("One or more diagnosis types are invalid or don't belong to your center.")
        
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        attrs['center_detail'] = user.center_detail
        attrs['test_done_by'] = user
        
        # Check if any diagnosis type is Franchise Lab
        diagnosis_type_ids = attrs.get('diagnosis_types', [])
        if diagnosis_type_ids:
            user_center = user.center_detail
            diagnosis_types = DiagnosisType.objects.filter(
                id__in=diagnosis_type_ids,
                center_detail=user_center
            )
            # Check if franchise_name is required (any diagnosis type has franchise lab category)
            has_franchise_lab = diagnosis_types.filter(category__is_franchise_lab=True).exists()
            
            if has_franchise_lab and not attrs.get('franchise_name'):
                raise serializers.ValidationError({
                    'franchise_name': "A franchise name is required when 'Franchise Lab' diagnosis type is selected."
                })
        
        # Remove temporary keys before the serializer saves the data
        attrs.pop('center_detail')
        attrs.pop('test_done_by')

        return attrs
    
    def create(self, validated_data):
        diagnosis_type_ids = validated_data.pop('diagnosis_types')
        user = self.context['request'].user
        
        # Create the bill instance
        bill = Bill.objects.create(
            center_detail=user.center_detail,
            test_done_by=user,
            **validated_data
        )
        
        # Create BillDiagnosisType entries for each diagnosis type
        user_center = user.center_detail
        diagnosis_types = DiagnosisType.objects.filter(
            id__in=diagnosis_type_ids,
            center_detail=user_center
        )
        
        for diagnosis_type in diagnosis_types:
            BillDiagnosisType.objects.create(
                bill=bill,
                diagnosis_type=diagnosis_type,
                price_at_time=diagnosis_type.price
            )
        
        # Calculate totals and incentive
        try:
            bill.calculate_totals_and_incentive()
        except DjangoValidationError as e:
            # Convert Django ValidationError to DRF ValidationError for proper API response
            raise DRFValidationError(e.message_dict if hasattr(e, 'message_dict') else {'error': str(e)})
        
        return bill
    
    def update(self, instance, validated_data):
        diagnosis_type_ids = validated_data.pop('diagnosis_types', None)
        
        user = self.context['request'].user
        
        # Update diagnosis types FIRST (before save) so validation uses new totals
        if diagnosis_type_ids is not None:
            # Clear existing diagnosis types
            instance.bill_diagnosis_types.all().delete()
            
            # Add new diagnosis types
            user_center = user.center_detail
            diagnosis_types = DiagnosisType.objects.filter(
                id__in=diagnosis_type_ids,
                center_detail=user_center
            )
            
            for diagnosis_type in diagnosis_types:
                BillDiagnosisType.objects.create(
                    bill=instance,
                    diagnosis_type=diagnosis_type,
                    price_at_time=diagnosis_type.price
                )
        
        # NOW update basic fields and save
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.center_detail = user.center_detail
        instance.test_done_by = user
        
        # Calculate totals BEFORE save so validation has correct total
        try:
            instance.calculate_totals_and_incentive()
        except DjangoValidationError as e:
            # Convert Django ValidationError to DRF ValidationError for proper API response
            raise DRFValidationError(e.message_dict if hasattr(e, 'message_dict') else {'error': str(e)})
        
        # Now save with correct totals - validation will pass
        try:
            instance.save()
        except DjangoValidationError as e:
            # Convert Django ValidationError to DRF ValidationError for proper API response
            raise DRFValidationError(e.message_dict if hasattr(e, 'message_dict') else {'error': str(e)})
        
        return instance
class IncentiveDiagnosisTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosisType
        fields = [ 'name', 'category', 'price']
class IncentiveFranchiseNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = FranchiseName
        fields= ['franchise_name']
class IncentiveDoctorSerializer (serializers.ModelSerializer):
    category_percentages = DoctorCategoryPercentageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Doctor
        fields=['id', 'first_name','last_name','hospital_name', 'ultrasound_percentage', 'pathology_percentage', 'ecg_percentage', 'xray_percentage', 'franchise_lab_percentage', 'others_percentage', 'category_percentages']
class IncentiveBillSerializer(serializers.ModelSerializer):
    """
    A read-only serializer for displaying nested bill details in reports.
    """
    diagnosis_types_output = serializers.SerializerMethodField()
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
            'diagnosis_types_output',
            'franchise_name',
            'date_of_bill',
            'bill_status',
            'total_amount',
            'paid_amount',
            'disc_by_doctor',       
            'disc_by_center',       
            'incentive_amount'
        ]
    
    def get_diagnosis_types_output(self, obj):
        """Return list of diagnosis types with details for this bill"""
        bill_diagnosis_types = obj.bill_diagnosis_types.select_related('diagnosis_type').all()
        return BillDiagnosisTypeSerializer(bill_diagnosis_types, many=True).data
        



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