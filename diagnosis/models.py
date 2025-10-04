from django.utils import timezone
from django.db import models
from django.forms import ValidationError
from django.core.validators import RegexValidator
from django.utils.text import slugify
from center_detail.models import CenterDetail
from authentication.models import StaffAccount
import os


def sample_report_file_upload_path(instance, filename):
    category = slugify(instance.diagnosis_type.category)
    specific_name = slugify(instance.diagnosis_name)
    extension = os.path.splitext(filename)[1]
    new_filename = f"{specific_name}{extension}"
    return os.path.join("sample_reports", category, new_filename)
def report_file_upload_path(instance, filename):
    # Get the file extension
    ext = filename.split('.')[-1]
    # Create new filename using bill number
    filename = f"{instance.bill.bill_number}.{ext}"
    # Return the full path
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
]
phone_regex = RegexValidator(
    regex=r'^\+?[0-9]{1,15}$',
    message='Invalid phone number. Please enter a valid phone number.'
)
class Doctor(models.Model):
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="center_detail")
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    hospital_name = models.CharField(max_length=30, blank=False, null = False)
    address = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15,unique = True, validators=[phone_regex]
)
    email = models.EmailField(blank=True, null= True, max_length=30)
    ultrasound_percentage = models.PositiveIntegerField(default=50,
       validators=[
           validate_incentive_percentage
        ]
    )

    pathology_percentage = models.PositiveIntegerField(default=50,
       validators=[
           validate_incentive_percentage
        ]
    )
    ecg_percentage = models.PositiveIntegerField(default=50,
       validators=[
           validate_incentive_percentage
        ]
    )
    xray_percentage = models.PositiveIntegerField(default=50,
        validators=[
           validate_incentive_percentage
        ]
    )
    franchise_lab_percentage = models.PositiveIntegerField(default=30,
        validators=[
           validate_incentive_percentage
        ]
    )


    def __str__(self):
        return f"{self.first_name} {self.last_name} {self.address} {self.phone_number}"


class DiagnosisType(models.Model):
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="center_detail_diagnosis")
    name = models.CharField(max_length=255)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=50)
    price = models.IntegerField()
    def __str__(self):
        return f"{self.category} - {self.name} - {self.price} - {self.center_detail.center_name}"

class FranchiseName(models.Model):
    franchise_name = models.CharField(max_length=50, unique=True)
    address = models.CharField(max_length=50 )
    phone_number = models.CharField(max_length=15, validators=[phone_regex])
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name='center_detail_franchise')
    def __str__(self):
        return f"{self.franchise_name}, {self.address}, {self.phone_number}"


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
    diagnosis_type = models.ForeignKey(DiagnosisType, on_delete=models.CASCADE, related_name="diagnosis_type")
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
        total = int(self.diagnosis_type.price or 0)
        paid = int(self.paid_amount or 0)
        bill_status = self.bill_status
        diagnosis_type = self.diagnosis_type
        center_disc = int(self.disc_by_center or 0)
        doctor_disc = int(self.disc_by_doctor or 0)

        if not diagnosis_type:
            raise ValidationError("Diagnosis type must be selected.")
        if diagnosis_type.category == "Franchise Lab" and not self.franchise_name:
            raise ValidationError({
                'franchise_name': "A franchise name is required for 'Franchise Lab' diagnosis types."
            })
        elif diagnosis_type.category != "Franchise Lab" and self.franchise_name:
            raise ValidationError({
                'franchise_name': 'Franchise name must be empty for non-franchise diagnosis types.'
            })
        # ----------------------------------------

        # Bill status and amount validations
        if bill_status not in dict(BILL_STATUS_CHOICES):
            raise ValidationError(f"Invalid bill status: {bill_status}. Must be one of {', '.join(dict(BILL_STATUS_CHOICES).keys())}.")
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

        if self.diagnosis_type:
            self.total_amount = int(self.diagnosis_type.price)
        
        # Run all model validations before saving
        self.full_clean()

        # Incentive calculation logic
        total = int(self.total_amount or 0)
        paid = int(self.paid_amount or 0)
        center_disc = int(self.disc_by_center or 0)
        doctor_disc = int(self.disc_by_doctor or 0)
        print(f"{doctor_disc} doctor discount")
        print(f"{center_disc} center discount")
        doctor_incentive = 0

        if self.referred_by_doctor and self.diagnosis_type:
            doctor = self.referred_by_doctor
            category = self.diagnosis_type.category
            
            percentage_map = {
                'Ultrasound': doctor.ultrasound_percentage,
                'Pathology': doctor.pathology_percentage,
                'ECG': doctor.ecg_percentage,
                'X-Ray': doctor.xray_percentage,
                'Franchise Lab': doctor.franchise_lab_percentage,
            }
            percent = percentage_map.get(category, 0)
            print(f"{percent} percent")
            full_incentive = (total * percent) // 100
            print(f"{full_incentive} full incentive")

            if total == paid+center_disc or (doctor_disc == 0 and center_disc > 0):
                print("if")
                doctor_incentive = full_incentive
            elif doctor_disc > 0:
                print("el if")
                doctor_incentive = full_incentive - doctor_disc
            else:
                print("else")
                doctor_incentive = full_incentive
        print(doctor_incentive)
        self.incentive_amount = doctor_incentive

        super().save(*args, **kwargs)
    
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

        file_size_limit = 8 * 1024 * 1024  # 8 MB size limit
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
    diagnosis_type = models.ForeignKey(
        DiagnosisType, 
        on_delete=models.CASCADE, 
        related_name="sample_reports"
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
        unique_together = ('diagnosis_type', 'diagnosis_name')

    def __str__(self):
        return f"{self.diagnosis_name} ({self.diagnosis_type.category})"
    
    def save(self, *args, **kwargs):
        if self.sample_report_file:
            filename = self.sample_report_file.name
            diagnosis_type_name = self.diagnosis_type
            extension = os.path.splitext(filename)[1]  # Extract file extension
            original_filename = os.path.splitext(filename)[0]  # Get original name without extension
            new_filename = f"{diagnosis_type_name}_{original_filename}{extension}"
            counter = 1

            while os.path.exists(os.path.join("media/sample_reports", new_filename)):
                new_filename = f"{diagnosis_type_name}_{original_filename}_{counter}{extension}"
                counter += 1
            old_file = None
            if self.pk:
                try:
                    old_instance = SampleTestReport.objects.get(pk=self.pk)
                    old_file = old_instance.sample_report_file
                except SampleTestReport.DoesNotExist:
                    old_file = None
            self.sample_report_file.name = os.path.join("sample_reports", new_filename)

        super().save(*args, **kwargs)
        if old_file and old_file != self.sample_report_file and os.path.isfile(os.path.join("media", old_file.name)):
            try:
                os.remove(os.path.join("media", old_file.name))
            except Exception as e:
                print(f"Failed to delete old file: {e}")

    def clean(self):
        if not self.sample_report_file:
            raise ValidationError("A sample report file is required.")

        file_size_limit = 8 * 1024 * 1024  # 8 MB limit
        allowed_formats = ('.doc', '.docx', '.rtf', '.txt')

        if self.sample_report_file.size > file_size_limit:
            raise ValidationError(f"File exceeds the {file_size_limit // (1024*1024)}MB limit.")

        if not self.sample_report_file.name.lower().endswith(allowed_formats):
            raise ValidationError(f"Invalid file format. Allowed formats: {', '.join(allowed_formats)}.")

        super().clean()

    def delete(self, *args, **kwargs):
        if self.sample_report_file and os.path.isfile(os.path.join("media", self.sample_report_file.name)):
            try:
                os.remove(os.path.join("media", self.sample_report_file.name))
            except Exception as e:
                print(f"Failed to delete report file: {e}")

        super().delete(*args, **kwargs)
    def __str__(self):
        return f"{self.diagnosis_name} - {self.diagnosis_type} - {self.center_detail.center_name}"