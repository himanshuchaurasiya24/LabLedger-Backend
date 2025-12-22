from django.utils import timezone
from django.db import models
from django.forms import ValidationError
from django.core.validators import RegexValidator
from django.utils.text import slugify
import uuid
from center_detail.models import CenterDetail
from authentication.models import StaffAccount
import os

def sample_report_file_upload_path(instance, filename):
    extension = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4()}{extension}"
    return os.path.join("sample_reports", unique_filename)
def report_file_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{instance.bill.bill_number}.{ext}"
    return os.path.join('reports/', filename)

def validate_age(value):
    if value > 150:
        raise ValidationError("Age cannot exceed 150 years.")

def validate_incentive_percentage(value):
    if value > 100:
        raise ValidationError("Incentive cannot exceed 100% .")
SEX_CHOICES = [
("Male", "Male"),
("Female", "Female"),
("Others", "Others"),
]   
BILL_STATUS_CHOICES = [
    ('Fully Paid', 'Fully Paid'),
    ('Partially Paid', 'Partially Paid'),
    ('Unpaid', 'Unpaid'),
]
CATEGORY_CHOICES = [
    ('X-Ray', 'X-Ray'),
    ('Pathology', 'Pathology'),
    ('ECG', 'ECG'),
    ('Ultrasound', 'Ultrasound'),
    ('Franchise Lab', 'Franchise Lab'),
    ('Others', 'Others'),
]
phone_regex = RegexValidator(
    regex=r'^\+?[0-9]{1,15}$',
    message='Invalid phone number. Please enter a valid phone number.'
)


# ========================
# DIAGNOSIS CATEGORY MODEL
# ========================

class DiagnosisCategory(models.Model):
    """
    Category for diagnosis types (e.g., Ultrasound, Pathology, ECG, etc.).
    Replaces hardcoded CATEGORY_CHOICES to allow dynamic category management.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_franchise_lab = models.BooleanField(
        default=False,
        help_text="If True, bills with this category require franchise name"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Diagnosis Category"
        verbose_name_plural = "Diagnosis Categories"
        ordering = ['name']
    
    def delete(self, *args, **kwargs):
        """
        Custom delete to ensure each diagnosis type's delete method is called
        (which implements smart cascade logic for bills)
        """
        # Get all diagnosis types in this category
        diagnosis_types = list(self.diagnosis_types.all())
        
        # Delete each one individually to trigger their custom delete logic
        for dt in diagnosis_types:
            dt.delete()
        
        # Now delete the category itself
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name


class Doctor(models.Model):
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="center_detail")
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    hospital_name = models.CharField(max_length=200, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Old percentage fields - kept for backward compatibility, nullable
    ultrasound_percentage = models.IntegerField(null=True, blank=True, default=0)
    pathology_percentage = models.IntegerField(null=True, blank=True, default=0)
    ecg_percentage = models.IntegerField(null=True, blank=True, default=0)
    xray_percentage = models.IntegerField(null=True, blank=True, default=0)
    franchise_lab_percentage = models.IntegerField(null=True, blank=True, default=0)
    others_percentage = models.IntegerField(null=True, blank=True, default=0)

    def __str__(self):
        return f"{self.first_name} {self.last_name} {self.address} {self.phone_number}"


# ========================
# DOCTOR CATEGORY PERCENTAGE
# ========================

class DoctorCategoryPercentage(models.Model):
    """
    Junction model to store dynamic incentive percentages for each category per doctor.
    Replaces individual percentage fields (ultrasound_percentage, pathology_percentage, etc.)
    """
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='category_percentages')
    category = models.ForeignKey(DiagnosisCategory, on_delete=models.CASCADE, related_name='doctor_percentages')
    percentage = models.PositiveIntegerField(
        default=50,
        validators=[validate_incentive_percentage]
    )

    class Meta:
        unique_together = ('doctor', 'category')
        verbose_name = "Doctor Category Percentage"
        verbose_name_plural = "Doctor Category Percentages"

    def __str__(self):
        return f"{self.doctor} - {self.category.name}: {self.percentage}%"


class DiagnosisType(models.Model):
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="center_detail_diagnosis")
    name = models.CharField(max_length=255)
    category = models.ForeignKey(DiagnosisCategory, on_delete=models.CASCADE, related_name='diagnosis_types')
    price = models.IntegerField()
    
    def delete(self, *args, **kwargs):
        """
        Smart cascade delete:
        - Delete bills that ONLY have this diagnosis type
        - Keep bills that have other diagnosis types (just remove this type)
        """
        # Find all bills that reference this diagnosis type
        bill_diagnosis_types = self.bill_references.all()
        
        # For each bill, check if it only has this diagnosis type
        for bdt in bill_diagnosis_types:
            bill = bdt.bill
            # Count how many diagnosis types this bill has
            diagnosis_count = bill.bill_diagnosis_types.count()
            
            if diagnosis_count == 1:
                # This is the only diagnosis type, delete the entire bill
                bill.delete()
            # If diagnosis_count > 1, the CASCADE will just remove the BillDiagnosisType entry
        
        # Now delete the diagnosis type itself (CASCADE will handle remaining BillDiagnosisType entries)
        super().delete(*args, **kwargs)
    
    def __str__(self):
        return f"{self.category.name} - {self.name} - {self.price} - {self.center_detail.center_name}"

class FranchiseName(models.Model):
    franchise_name = models.CharField(max_length=50, unique=True)
    address = models.CharField(max_length=50 )
    phone_number = models.CharField(max_length=15, validators=[phone_regex])
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name='center_detail_franchise')
    def __str__(self):
        return f"{self.franchise_name}, {self.address}, {self.phone_number}"

class BillDiagnosisType(models.Model):
    """Junction model to link Bill with multiple DiagnosisTypes"""
    bill = models.ForeignKey('Bill', on_delete=models.CASCADE, related_name='bill_diagnosis_types')
    diagnosis_type = models.ForeignKey(DiagnosisType, on_delete=models.CASCADE, related_name='bill_references')
    price_at_time = models.IntegerField()  # Store price at time of bill creation
    
    class Meta:
        unique_together = ('bill', 'diagnosis_type')
    
    def __str__(self):
        return f"{self.bill.bill_number} - {self.diagnosis_type.name}"

class Bill(models.Model):
    bill_number = models.CharField(max_length=22, unique=True, editable=False)
    date_of_test = models.DateTimeField(default=timezone.now)
    patient_name = models.CharField(max_length=60)
    patient_age = models.PositiveIntegerField(validators=[validate_age])
    patient_sex = models.CharField(choices=SEX_CHOICES, max_length=10)
    patient_phone_number = models.PositiveBigIntegerField(
        default=9999999999,  # Placeholder for old records
        validators=[
            RegexValidator(
                regex=r'^\d{10,15}$', 
                message="Phone number must be between 10 and 15 digits."
            )
        ]
    )
    diagnosis_types = models.ManyToManyField(DiagnosisType, through='BillDiagnosisType', related_name="bills")
    test_done_by = models.ForeignKey(StaffAccount, on_delete=models.CASCADE, related_name="test_done_by", null=True, blank=True)
    referred_by_doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, null=True, blank=True, related_name="referred_patients_by_doctor"
    )
    franchise_name = models.ForeignKey(
        FranchiseName,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    date_of_bill = models.DateTimeField(default=timezone.now)
    bill_status = models.CharField(choices=BILL_STATUS_CHOICES, max_length=15, default='Fully Paid')
    total_amount = models.IntegerField(editable=False)
    paid_amount = models.IntegerField(blank=True, default=0)
    disc_by_center = models.IntegerField(default=0)
    disc_by_doctor = models.IntegerField(default=0)
    incentive_amount = models.IntegerField(editable=False, default=0)
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="center_detail_bill")

    def clean(self):
        # Note: For many-to-many fields, we need to validate after the instance is saved
        # This clean() method will handle basic validations that don't require m2m data
        paid = int(self.paid_amount or 0)
        bill_status = self.bill_status
        center_disc = int(self.disc_by_center or 0)
        doctor_disc = int(self.disc_by_doctor or 0)

        # Bill status validations
        if bill_status not in dict(BILL_STATUS_CHOICES):
            raise ValidationError(f"Invalid bill status: {bill_status}. Must be one of {', '.join(dict(BILL_STATUS_CHOICES).keys())}.")
        
        # For M2M fields, total_amount validation needs to happen after save
        # We'll do a simple check here if total_amount is already set
        if hasattr(self, 'total_amount') and self.total_amount:
            total = int(self.total_amount or 0)
            if bill_status == 'Fully Paid' and total != paid + center_disc + doctor_disc:
                raise ValidationError({
                    'paid_amount': f"Total amount ({total}) must be equal to paid ({paid}) + center discount ({center_disc}) + doctor discount ({doctor_disc}) for a fully paid bill."
                })
            if bill_status == 'Partially Paid' and total <= paid + center_disc + doctor_disc:
                raise ValidationError({
                    'paid_amount': f"For a partially paid bill, total amount ({total}) must be greater than paid ({paid}) + discounts ({center_disc + doctor_disc})."
                })
        
        if bill_status == 'Unpaid' and (paid > 0 or center_disc > 0 or doctor_disc > 0):
            raise ValidationError({
                'paid_amount': "For an unpaid bill, paid amount and all discounts must be zero."
            })

    def save(self, *args, **kwargs):
        if not self.bill_number:
            now = timezone.now()
            timestamp = now.strftime('%Y%m%d%H%M%S%f')
            self.bill_number = f"LL{timestamp}"

        # For new instances, we need to save first before we can add m2m relationships
        is_new = self.pk is None
        
        # Set total_amount to 0 initially for new bills (will be updated after m2m is set)
        if is_new:
            if self.total_amount is None:
                self.total_amount = 0
            if self.incentive_amount is None:
                self.incentive_amount = 0
        
        # Run basic validations
        self.full_clean()
        
        # Save the bill instance first
        super().save(*args, **kwargs)
        
    def calculate_totals_and_incentive(self):
        """
        Calculate total_amount and incentive_amount based on all diagnosis types.
        This should be called after the m2m relationship is set up.
        """
        # Calculate total amount from all diagnosis types
        bill_diagnosis_types = self.bill_diagnosis_types.all()
        
        if not bill_diagnosis_types.exists():
            self.total_amount = 0
            self.incentive_amount = 0
            super(Bill, self).save(update_fields=['total_amount', 'incentive_amount'])
            return
        
        # Check if any diagnosis type is Franchise Lab
        has_franchise_lab = any(bdt.diagnosis_type.category == 'Franchise Lab' for bdt in bill_diagnosis_types)
        has_non_franchise = any(bdt.diagnosis_type.category != 'Franchise Lab' for bdt in bill_diagnosis_types)
        
        # Validate franchise name requirement
        if has_franchise_lab and not self.franchise_name:
            raise ValidationError({
                'franchise_name': "A franchise name is required when 'Franchise Lab' diagnosis type is selected."
            })
        elif not has_franchise_lab and has_non_franchise and self.franchise_name:
            # Clear franchise name if no franchise lab diagnosis types
            self.franchise_name = None
        
        # Calculate total amount
        total_amount = sum(bdt.price_at_time for bdt in bill_diagnosis_types)
        self.total_amount = total_amount
        
        # Calculate incentive
        paid = int(self.paid_amount or 0)
        center_disc = int(self.disc_by_center or 0)
        doctor_disc = int(self.disc_by_doctor or 0)
        total_incentive = 0
        
        if self.referred_by_doctor:
            doctor = self.referred_by_doctor
            
            # Calculate incentive for each diagnosis type
            for bdt in bill_diagnosis_types:
                category = bdt.diagnosis_type.category
                price = bdt.price_at_time
                
                # Get doctor's percentage for this category dynamically
                try:
                    category_percentage = doctor.category_percentages.get(category=category)
                    percent = category_percentage.percentage
                except DoctorCategoryPercentage.DoesNotExist:
                    # Default to 0 if no percentage is set for this category
                    percent = 0
                
                diagnosis_incentive = (price * percent) // 100
                total_incentive += diagnosis_incentive
            
            # Apply discounts to the total incentive
            if total_amount == paid + center_disc or (doctor_disc == 0 and center_disc > 0):
                self.incentive_amount = total_incentive
            elif doctor_disc > 0:
                self.incentive_amount = total_incentive - doctor_disc
            else:
                self.incentive_amount = total_incentive
        else:
            self.incentive_amount = 0
        
        # Validate bill status with updated total
        paid = int(self.paid_amount or 0)
        bill_status = self.bill_status
        
        if bill_status == 'Fully Paid' and self.total_amount != paid + center_disc + doctor_disc:
            raise ValidationError({
                'paid_amount': f"Total amount ({self.total_amount}) must be equal to paid ({paid}) + center discount ({center_disc}) + doctor discount ({doctor_disc}) for a fully paid bill."
            })
        if bill_status == 'Partially Paid' and self.total_amount <= paid + center_disc + doctor_disc:
            raise ValidationError({
                'paid_amount': f"For a partially paid bill, total amount ({self.total_amount}) must be greater than paid ({paid}) + discounts ({center_disc + doctor_disc})."
            })
        
        # Save with updated totals
        super(Bill, self).save(update_fields=['total_amount', 'incentive_amount', 'franchise_name'])
        
    def __str__(self):
        doctor_name = "No Doctor"
        if self.referred_by_doctor:
            doctor_name = f"Dr. {self.referred_by_doctor.first_name} {self.referred_by_doctor.last_name}"
        return f"{self.bill_number} - {self.patient_name} - Ref by {doctor_name}"

class PatientReport(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="report")
    report_file = models.FileField(upload_to=report_file_upload_path, blank=False, null=False)
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="center_detail_report")
    def __str__(self):
        return f"{self.bill.date_of_bill.strftime('%d-%m-%Y')} Report for {self.bill.patient_name} Ref by Dr. {self.bill.referred_by_doctor.first_name} {self.bill.referred_by_doctor.last_name}"

    def save(self, *args, **kwargs):
        if self.report_file:
            bill_number = self.bill.bill_number
            extension = os.path.splitext(self.report_file.name)[1]
            new_filename = f"{bill_number}{extension}"

            self.report_file.name = new_filename

            existing_reports = PatientReport.objects.filter(bill=self.bill).exclude(pk=self.pk)
            for report in existing_reports:
                if report.report_file and os.path.isfile(report.report_file.path):
                    try:
                        os.remove(report.report_file.path)
                    except Exception as e:
                        print(f"Failed to delete existing report file: {e}")
                report.delete()

        super().save(*args, **kwargs)


    def clean(self):
        if not self.report_file:
            raise ValidationError("A report file is required.")

        file_size_limit = 1 * 1024 * 1024  # 1 MB size limit
        allowed_formats = ('.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx')

        if self.report_file.size > file_size_limit:
            raise ValidationError(f"Report file exceeds the {file_size_limit // (1024*1024)}MB limit.")

        if not self.report_file.name.lower().endswith(allowed_formats):
            raise ValidationError(f"Invalid file format. Allowed formats: {', '.join(allowed_formats)}.")

        super().clean()
    def delete(self, *args, **kwargs):
        if self.report_file and os.path.isfile(self.report_file.path):
            try:
                os.remove(self.report_file.path)
            except Exception as e:
                print(f"Failed to delete report file: {e}")

        super().delete(*args, **kwargs)

class SampleTestReport(models.Model):
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        null=True
    )
    diagnosis_name = models.CharField(max_length=255)
    sample_report_file = models.FileField(
        upload_to=sample_report_file_upload_path,
        blank=False,
        null=False
    )
    center_detail = models.ForeignKey(
        CenterDetail,
        on_delete=models.CASCADE,
        related_name="center_detail_sample_test_report"
    )

    class Meta:
        unique_together = ('category', 'diagnosis_name')

    def __str__(self):
        return f"{self.diagnosis_name} - {self.category} - {self.center_detail.center_name}"

    def save(self, *args, **kwargs):
        """
        ✅ Simplified save method.
        The complex file renaming logic is removed and handled by `upload_to`.
        This method now only handles deleting an old file if a new one is
        uploaded during an update.
        """
        if self.pk:  # Check if this is an update to an existing object
            try:
                old_instance = SampleTestReport.objects.get(pk=self.pk)
                # If the file has been changed, delete the old one from the filesystem
                if old_instance.sample_report_file != self.sample_report_file:
                    if old_instance.sample_report_file and os.path.isfile(old_instance.sample_report_file.path):
                        os.remove(old_instance.sample_report_file.path)
            except SampleTestReport.DoesNotExist:
                pass  # This is a new instance, so do nothing

        super().save(*args, **kwargs)

    def clean(self):
        # Your clean method logic is good and remains unchanged.
        if not self.sample_report_file:
            raise ValidationError("A sample report file is required.")

        file_size_limit = 1 * 1024 * 1024  # 1 MB limit
        allowed_formats = ('.doc', '.docx', '.rtf', '.txt')

        if self.sample_report_file.size > file_size_limit:
            raise ValidationError(f"File exceeds the {file_size_limit // (1024*1024)}MB limit.")

        if not self.sample_report_file.name.lower().endswith(allowed_formats):
            raise ValidationError(f"Invalid file format. Allowed formats: {', '.join(allowed_formats)}.")

        super().clean()

    def delete(self, *args, **kwargs):
        # Your delete method is correct and remains unchanged.
        # It ensures the physical file is deleted when the database record is.
        if self.sample_report_file and os.path.isfile(self.sample_report_file.path):
            try:
                os.remove(self.sample_report_file.path)
            except Exception as e:
                print(f"Failed to delete report file: {e}")
        
        super().delete(*args, **kwargs)