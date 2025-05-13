from django.db import models
from center_details.models import CenterDetail
from authentication.models import StaffAccount

class Doctor(models.Model):
    name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="doctors")

    def __str__(self):
        return self.name

class Service(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="services")

    def __str__(self):
        return f"{self.name} - {self.center_detail.name}"

class Patient(models.Model):
    name = models.CharField(max_length=255)
    age = models.IntegerField()
    phone_number = models.CharField(max_length=15, unique=True)
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name="patients")
    
    referred_by_doctor = models.ForeignKey(
        Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name="referred_patients_by_doctor"
    )
    referred_by_staff = models.ForeignKey(
        StaffAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name="referred_patients_by_staff"
    )

    def __str__(self):
        return self.name


class Bill(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    
    # Allow referrals by either a doctor or a staff member
    referred_by_doctor = models.ForeignKey(
        Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name="bills_referred_by_doctor"
    )
    referred_by_staff = models.ForeignKey(
        StaffAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name="bills_referred_by_staff"
    )

    def __str__(self):
        return f"Bill for {self.patient.name} - {self.amount}"

class Incentive(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="incentives")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="incentives")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="incentives")
    incentive_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.doctor.name} - {self.service.name} - {self.incentive_amount}"