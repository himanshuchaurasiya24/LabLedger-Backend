from django.utils import timezone
from django.db import models
from django.forms import ValidationError
import uuid
from django.db import models
from center_detail.models import CenterDetail
from authentication.models import StaffAccount
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
bill_status_choices = [
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
    bill_status = models.CharField(choices=bill_status_choices, max_length=15)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    disc_by_center = models.IntegerField(default=0)
    disc_by_doctor = models.IntegerField(default=0)
    incentive_amount = models.DecimalField(max_digits=10, decimal_places=2)
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="center_detail_bill")
    


    def save(self, *args, **kwargs):
        if not self.bill_number:
            now = timezone.now()
            timestamp = now.strftime('%Y%m%d%H%M%S%f')  # e.g., 20250528161530234567
            self.bill_number = f"LL{timestamp}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.bill_number
class Report(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="report")
    report_file = models.FileField(upload_to='reports/')

    def __str__(self):
        return f"Report for {self.bill.bill_number} - {self.report_status}"
    def save(self, *args, **kwargs):
        if not self.report_file:
            raise ValidationError("Report file cannot be empty.")
        super().save(*args, **kwargs)
    def clean(self):
        if not self.report_file:
            raise ValidationError("Report file cannot be empty.")
        if self.report_file.size > 8 * 1024 * 1024:
            raise ValidationError("Report file size cannot exceed 8 MB.")
        if not self.report_file.name.endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            raise ValidationError("Report file must be a PDF, JPG, JPEG, or PNG.")
        super().clean()

    def delete(self, *args, **kwargs):
        if self.report_file:
            self.report_file.delete(save=False)
        super().delete(*args, **kwargs)