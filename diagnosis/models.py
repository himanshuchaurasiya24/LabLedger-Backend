import os
from django.utils import timezone
from django.db import models
from django.forms import ValidationError
import uuid
from django.db import models
from center_detail.models import CenterDetail
from authentication.models import StaffAccount

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
    ('Paid', 'Paid'),
    ('Partially Paid', 'Partially Paid'),
    ('Unpaid', 'Unpaid'),
]
CATEGORY_CHOICES = [
    ('X-ray', 'X-ray'),
    ('Pathology', 'Pathology'),
    ('ECG', 'ECG'),
    ('Ultrasound', 'Ultrasound'),
]

class Doctor(models.Model):
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="center_detail")
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    address = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True)
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

    def __str__(self):
        return f"{self.first_name} {self.last_name} {self.address} {self.phone_number}"


class DiagnosisType(models.Model):
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="center_detail_diagnosis")
    name = models.CharField(max_length=255)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"{self.category} - {self.name} - {self.price}"






class Bill(models.Model):
    bill_number = models.CharField(max_length=20, unique=True, editable=False)
    date_of_test = models.DateTimeField(default=timezone.now)
    patient_name = models.CharField(max_length=60)
    patient_age = models.PositiveIntegerField(validators=[validate_age])
    patient_sex = models.CharField(choices=SEX_CHOICES, max_length=10)
    test_type = models.ForeignKey(DiagnosisType, on_delete=models.CASCADE, related_name="test_type")
    test_done_by = models.ForeignKey(StaffAccount, on_delete=models.CASCADE, related_name="test_done_by")
    referred_by_doctor = models.ForeignKey(
        Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name="referred_patients_by_doctor"
    )
    date_of_bill = models.DateTimeField(default=timezone.now)
    bill_status = models.CharField(choices=BILL_STATUS_CHOICES, max_length=15)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    disc_by_center = models.IntegerField(default=0)
    disc_by_doctor = models.IntegerField(default=0)
    incentive_amount = models.DecimalField(max_digits=10, decimal_places=2)
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="center_detail_bill")
    


    def save(self, *args, **kwargs):
        if not self.bill_number:
            now = timezone.now()
            timestamp = now.strftime('%Y%m%d%H%M%S%f')
            self.bill_number = f"LL{timestamp}"

    # Always set total_amount from diagnosis price, overwrite any manual value
        if self.test_type:
            self.total_amount = self.test_type.price

        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.bill_number} {self.patient_name} {self.patient_age} {self.patient_sex} Ref by Dr. {self.referred_by_doctor.first_name} {self.referred_by_doctor.last_name}"
    

class Report(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="report")
    report_file = models.FileField(upload_to=report_file_upload_path, blank=False, null=False)
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="center_detail_report")
    def __str__(self):
        return f"{self.bill.date_of_bill.strftime('%d-%m-%Y')} Report for {self.bill.patient_name} Ref by Dr. {self.bill.referred_by_doctor.first_name} {self.bill.referred_by_doctor.last_name}"

    def save(self, *args, **kwargs):
        # Only attempt to get the old file if the instance already exists
        if self.pk:
            try:
                old_file = Report.objects.get(pk=self.pk).report_file
            except Report.DoesNotExist:
                old_file = None
        else:
            old_file = None

        super().save(*args, **kwargs)

        # After saving, delete the old file if it's different from the new file
        if old_file and old_file != self.report_file:
            if old_file.name and os.path.isfile(old_file.path):
                try:
                    os.remove(old_file.path)
                except Exception as e:
                    print(f"Failed to delete old file: {e}")

    def clean(self):
        if not self.report_file:
            raise ValidationError("Report file cannot be empty.")
        if self.report_file.size > 8 * 1024 * 1024:
            raise ValidationError("Report file size cannot exceed 8 MB.")
        if not self.report_file.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            raise ValidationError("Report file must be a PDF, JPG, JPEG, or PNG.")
        super().clean()

    def delete(self, *args, **kwargs):
        if self.report_file:
            self.report_file.delete(save=False)
        super().delete(*args, **kwargs)