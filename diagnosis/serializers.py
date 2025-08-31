from authentication.serializers import *
from center_detail.serializers import *
from .models import *
from rest_framework import serializers
from .models import *
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

class MinimalDiagnosisTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosisType
        fields = ['id', 'name', 'category', 'price']
class MinimalBillSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Bill
        fields = ['id', 'bill_number', 'patient_name', 'patient_age', 'patient_sex']
class MinimalDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields= ['id','first_name', 'last_name', 'address', 'email']
class DiagnosisTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiagnosisType
        fields = '__all__'
        read_only_fields = ['center_detail']  # ✅ center_detail auto-filled

    def validate(self, attrs):
        # only check if center_detail is already present (like during update from admin)
        user_center = self.context['request'].user.center_detail

        if attrs.get('center_detail') and attrs['center_detail'] != user_center:
            raise serializers.ValidationError({
                'center_detail': 'Diagnosis type must belong to your center.'
            })

        return attrs



class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = "__all__"
        read_only_fields = ['id','center_detail']
    def validate(self, attrs):
        user_center = self.context['request'].user.center_detail

        if attrs.get('center_detail') and attrs['center_detail'] != user_center:
            raise serializers.ValidationError({
                'center_detail': 'Doctor must belong to your center.'
            })

        return attrs


class FranchiseNameSerializer(serializers.ModelSerializer):
    center_detail = MinimalCenterDetailSerializer(read_only=True)

    class Meta:
        model = FranchiseName
        fields = '__all__'
        read_only_fields = ('center_detail',)

    def validate(self, attrs):
        user = self.context['request'].user
        user_center = user.center_detail
        attrs['center_detail'] = user_center

        # Prevent duplicate franchise name within same center
        if FranchiseName.objects.filter(franchise_name=attrs['franchise_name'], center_detail=user_center).exists():
            raise serializers.ValidationError({'franchise_name': 'This franchise name already exists in your center.'})
        return attrs

class BillSerializer(serializers.ModelSerializer):
    # INPUT fields
    diagnosis_type = serializers.PrimaryKeyRelatedField(
        queryset=DiagnosisType.objects.all(),
        write_only=True
    )
    referred_by_doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )

    # OUTPUT nested fields
    diagnosis_type_output = MinimalDiagnosisTypeSerializer(source="diagnosis_type", read_only=True)
    referred_by_doctor_output = MinimalDoctorSerializer(source="referred_by_doctor", read_only=True)
    test_done_by = MinimalStaffAccountSerializer(read_only=True)
    center_detail = MinimalCenterDetailSerializer(read_only=True)

    # Extra field for search highlight
    match_reason = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = "__all__"
        read_only_fields = (
            "bill_number",
            "test_done_by",
            "center_detail",
            "incentive_amount",
            "total_amount",
        )

    def get_match_reason(self, obj):
        query = self.context.get("query", "").lower()
        if not query:
            return None

        reasons = []
        if query in str(obj.bill_number).lower():
            reasons.append("Bill Number")
        if query in (obj.patient_name or "").lower():
            reasons.append("Patient Name")
        if query in getattr(obj.diagnosis_type, "name", "").lower():
            reasons.append("Diagnosis Type")
        if query in (getattr(obj.referred_by_doctor, "first_name", "") + " " +
                     getattr(obj.referred_by_doctor, "last_name", "")).lower():
            reasons.append("Referred Doctor")
        if query in (obj.franchise_name or "").lower():
            reasons.append("Franchise")
        if query in (obj.bill_status or "").lower():
            reasons.append("Bill Status")

        return reasons if reasons else None

    def validate(self, attrs):
        user = self.context["request"].user
        user_center = user.center_detail
        attrs["center_detail"] = user_center

        diagnosis_type = attrs.get("diagnosis_type")
        if diagnosis_type and diagnosis_type.center_detail != user_center:
            raise serializers.ValidationError({
                "diagnosis_type": "Diagnosis type must belong to your center."
            })

        referred_by_doctor = attrs.get("referred_by_doctor")
        if referred_by_doctor and referred_by_doctor.center_detail != user_center:
            raise serializers.ValidationError({
                "referred_by_doctor": "Doctor must belong to your center."
            })

        instance = Bill(**attrs)
        try:
            instance.full_clean()
        except DjangoValidationError as e:
            raise DRFValidationError(e.message_dict)

        return attrs

class PatientReportSerializer(serializers.ModelSerializer):
    bill = serializers.PrimaryKeyRelatedField(queryset=Bill.objects.all(), write_only=True)
    bill_output = MinimalBillSerializer(read_only=True, source='bill')
    
    # Make center_detail hidden and automatically assigned
    center_detail = serializers.HiddenField(default=serializers.CurrentUserDefault())
    center_detail_output = MinimalCenterDetailSerializer(read_only=True, source='center_detail')

    class Meta:
        model = PatientReport
        fields = '__all__'

    def validate(self, attrs):
        user = self.context['request'].user
        user_center = user.center_detail

        # Forcefully assign center_detail from user
        attrs['center_detail'] = user_center

        if attrs.get('bill') and attrs['bill'].center_detail != user_center:
            raise serializers.ValidationError({
                'bill': 'Patient report must belong to your center.'
            })

        return attrs


class SampleTestReportSerializer(serializers.ModelSerializer):
    center_detail = serializers.PrimaryKeyRelatedField(queryset= CenterDetail.objects.all(), write_only=True)
    center_detail_output = MinimalCenterDetailSerializer(read_only=True, source='center_detail')
    class Meta:
        model = SampleTestReport
        fields = ['id', 'diagnosis_name', 'diagnosis_type', 'sample_report_file', 'center_detail','center_detail_output']

    def validate(self, attrs):
        user_center = getattr(self.context['request'].user, 'center_detail', None)
        if not user_center or attrs['center_detail'] != user_center:
            raise serializers.ValidationError({
                'center_detail': 'Sample test report must belong to your center.'
    })

        return attrs
