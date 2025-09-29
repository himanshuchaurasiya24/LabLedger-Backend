from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from center_detail.models import CenterDetail


class StaffAccountManager(BaseUserManager):
    """
    Custom manager for the StaffAccount model.
    """
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        if not username:
            raise ValueError("Users must have a username.")

        user = self.model(
            username=username,
            email=self.normalize_email(email),
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_staff', True) # Ensure is_staff is also set
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_admin') is not True:
            raise ValueError('Superuser must have is_admin=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)


class StaffAccount(AbstractUser):
    """
    Custom user model where 'is_admin' controls staff access.
    """
    # Base fields
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
    address = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True)
    
    # Relational field
    center_detail = models.ForeignKey(
        CenterDetail,
        on_delete=models.CASCADE,
        related_name='staff_accounts',
        blank=True,
        null=True
    )
    
    # Permission and status fields
    is_admin = models.BooleanField(
        'admin status',
        default=False,
        help_text='Designates that this user can log into the admin site.'
    )
    is_staff = models.BooleanField(
        'staff status',
        default=False,
        help_text='Required by Django admin. Automatically synced with "admin status".'
    )
    is_locked = models.BooleanField(
        default=False,
        help_text='If true, the user is locked out and cannot log in.'
    )
    
    # ✅ Fields required by the custom token serializer
    failed_login_attempts = models.IntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)
    
    # Manager and required settings
    objects = StaffAccountManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        # Automatically sync is_staff with is_admin before saving
        self.is_staff = self.is_admin
        super().save(*args, **kwargs)