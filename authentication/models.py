from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.contrib.auth.models import BaseUserManager

from django.contrib.auth.models import BaseUserManager

from django.contrib.auth.models import BaseUserManager

from center_detail.models import CenterDetail


class StaffAccountManager(BaseUserManager):
    def create_user(self, username, email, password,first_name='enter first_name', last_name='enter last_name', phone_number='0000000000', address='enter address'):
        if not email:
            raise ValueError("Users must have an email address")
        if not username:
            raise ValueError("Users must have a username")
        if not password:
            raise ValueError("Users must provide a password")
        if not first_name:
            raise ValueError("Users must have a first name")
        if not last_name:
            raise ValueError("Users must have a last name")
        if not phone_number:
            raise ValueError("Users must have a phone number")
        if not address:
            raise ValueError("Users must have an address")
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            address=address,
            is_admin=False
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email,password, first_name='enter first_name', last_name='enter last_name', phone_number='0000000000', address='enter address'):
        if not password:
            raise ValueError("Superusers must provide a password")
        if not username:
            raise ValueError("Superusers must have a username")
        if not email:
            raise ValueError("Superusers must have an email address")
        if not first_name:
            raise ValueError("Superusers must have a first name")
        if not last_name:
            raise ValueError("Superusers must have a last name")
        if not phone_number:
            raise ValueError("Superusers must have a phone number")
        if not address:
            raise ValueError("Superusers must have an address")
        
        user = self.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            address=address,
            password=password
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user





class StaffAccount(AbstractUser):
    username = models.CharField(
        max_length=20, 
        unique=True, 
        validators=[
            RegexValidator(
                regex=r'^[a-z][a-zA-Z0-9]*$', 
                message="Username must start with a lowercase letter and contain only letters and numbers."
            )
        ]
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_staff = models.BooleanField(default=True)
    address = models.CharField(max_length=100)
    is_admin = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, unique=True)
    center_detail = models.ForeignKey(CenterDetail, on_delete=models.CASCADE, related_name='center_detail_staff', blank=True, null=True)
    objects = StaffAccountManager()


    def __str__(self):
        return self.username
    


    