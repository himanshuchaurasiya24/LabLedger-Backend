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
    if value > 150:
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

    pathology_incentive = models.PositiveIntegerField(default=50,
       validators=[
           validate_incentive_percentage
        ]
    )
    ecg_incentive = models.PositiveIntegerField(default=50,
       validators=[
           validate_incentive_percentage
        ]
    )
    xray_incentive = models.PositiveIntegerField(default=50,
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
            self.bill_number = f"RKDC{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Bill {self.bill_number} for {self.patient_name} - {self.total_amount}"