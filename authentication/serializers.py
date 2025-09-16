# authentication/serializers.py

from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import StaffAccount
from center_detail.serializers import CenterDetailSerializer, CenterDetailTokenSerializer

StaffAccount = get_user_model()


# --- User & Account Serializers ---
class StaffAccountSerializer(serializers.ModelSerializer):
    center_detail = CenterDetailSerializer(read_only=True)
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = StaffAccount
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'phone_number', 'address', 'is_admin', 'center_detail', 
            'password', 'is_locked'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }

    def validate_username(self, value):
        if self.instance:
            if StaffAccount.objects.exclude(pk=self.instance.pk).filter(username=value).exists():
                raise serializers.ValidationError("A user with this username already exists.")
        else:
            if StaffAccount.objects.filter(username=value).exists():
                raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        if self.instance:
            if StaffAccount.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
                raise serializers.ValidationError("A user with this email already exists.")
        else:
            if StaffAccount.objects.filter(email=value).exists():
                raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_number(self, value):
        if self.instance:
            if StaffAccount.objects.exclude(pk=self.instance.pk).filter(phone_number=value).exists():
                raise serializers.ValidationError("A user with this phone number already exists.")
        else:
            if StaffAccount.objects.filter(phone_number=value).exists():
                raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def create(self, validated_data):
        if 'password' not in validated_data:
            raise serializers.ValidationError({"password": ["This field is required for user creation."]})
            
        request = self.context.get('request')
        center_detail = None
        if request and hasattr(request.user, 'center_detail'):
            center_detail = request.user.center_detail
            
        password = validated_data.pop('password')
        user = StaffAccount.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data['phone_number'],
            address=validated_data['address'],
            is_admin=validated_data.get('is_admin', False),
            is_staff=validated_data.get('is_admin', False),
            is_superuser=validated_data.get('is_admin', False),
            center_detail=center_detail
        )
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data.pop('password')
        
        requesting_user = self.context['request'].user
        
        # --- FIX [2]: PREVENT NON-ADMINS FROM CHANGING PRIVILEGES ---
        # If a non-admin tries to change is_admin status, silently ignore it.
        if 'is_admin' in validated_data and not requesting_user.is_admin:
            validated_data.pop('is_admin')
        
        # This existing logic for is_locked is correct.
        if 'is_locked' in validated_data and requesting_user.is_admin:
            if validated_data['is_locked'] is False:
                instance.failed_login_attempts = 0
                instance.lockout_until = None
        elif 'is_locked' in validated_data and not requesting_user.is_admin:
            validated_data.pop('is_locked')
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class MinimalStaffAccountSerializer(serializers.ModelSerializer):     
    class Meta:
        model = StaffAccount
        fields = ['id', 'first_name', 'last_name']


# --- Password Management Serializers ---
class AdminPasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'},
        min_length=1,
        error_messages={
            'required': 'Password is required.', 
            'blank': 'Password cannot be blank.', 
            'min_length': 'Password must be at least 1 character long.'
        }
    )

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def update(self, instance, validated_data):
        instance.set_password(validated_data['password'])
        instance.save()
        return instance


class UserPasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'},
        error_messages={
            'required': 'Current password is required.', 
            'blank': 'Current password cannot be blank.'
        }
    )
    new_password = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'},
        error_messages={
            'required': 'New password is required.', 
            'blank': 'New password cannot be blank.'
        }
    )

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Your current password was entered incorrectly.")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, data):
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError({
                "new_password": ["New password must be different from the current password."]
            })
        return data

    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance


# --- Token & Authentication Serializer ---
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    MAX_FAILED_ATTEMPTS = 3
    LOCKOUT_DURATION = timedelta(minutes=15)

    def validate(self, attrs):
        username_or_email = attrs.get(self.username_field)
        
        user = StaffAccount.objects.filter(
            Q(username__iexact=username_or_email) | Q(email__iexact=username_or_email)
        ).first()

        # --- FIX [1]: PREVENT LOGIN IF ACCOUNT IS LOCKED ---
        if user and user.is_locked:
            # Check if it's a temporary lockout that is still active
            if user.lockout_until and timezone.now() < user.lockout_until:
                time_left = user.lockout_until - timezone.now()
                minutes_left = (time_left.seconds + 59) // 60 
                raise PermissionDenied(f"Account locked due to failed attempts. Please try again in {minutes_left} minute(s).")
            # Check if it's a manual/permanent lock
            else:
                raise PermissionDenied("Your account is locked. Please contact an administrator.")

        # The rest of the validation logic proceeds only if the user is not locked
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= self.MAX_FAILED_ATTEMPTS:
                    user.is_locked = True
                    user.lockout_until = timezone.now() + self.LOCKOUT_DURATION
                    user.save()
                    raise AuthenticationFailed(f"Your account has been locked for {self.LOCKOUT_DURATION.seconds // 60} minutes due to too many failed login attempts.")
                user.save()
            raise AuthenticationFailed("Invalid username or password.")
        
        # This code now correctly runs only for users who were not locked to begin with
        if self.user:
            self.user.failed_login_attempts = 0
            # We reset lock fields in case a temporary lock had expired
            self.user.is_locked = False
            self.user.lockout_until = None
            self.user.save()

        data['is_admin'] = self.user.is_admin
        data['username'] = self.user.username
        data['first_name'] = self.user.first_name
        data['last_name'] = self.user.last_name
        data['id'] = self.user.id
        data['is_locked'] = self.user.is_locked

        center = getattr(self.user, "center_detail", None)
        if center:
            center_data = CenterDetailTokenSerializer(center).data
            data["center_detail"] = center_data
        else:
            data["center_detail"] = None

        return data