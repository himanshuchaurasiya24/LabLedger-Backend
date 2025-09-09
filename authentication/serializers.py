# serializers.py - FIXED VERSION

from rest_framework import serializers
from authentication.models import StaffAccount
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# Import Django's password validator and core exception
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from center_detail.models import Subscription
from center_detail.serializers import CenterDetailSerializer, CenterDetailTokenSerializer, SubscriptionSerializer

# --- FIXED StaffAccount Serializer ---
class StaffAccountSerializer(serializers.ModelSerializer):
    center_detail = CenterDetailSerializer(read_only=True)
    password = serializers.CharField(write_only=True, required=False)  # Make password optional
    
    class Meta:
        model = StaffAccount
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'address', 'is_admin', 'center_detail', 'password']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}  # Optional for updates
        }

    def validate_username(self, value):
        """Custom validation for username"""
        if self.instance:  # This is an update
            if StaffAccount.objects.exclude(pk=self.instance.pk).filter(username=value).exists():
                raise serializers.ValidationError("A user with this username already exists.")
        else:  # This is a create
            if StaffAccount.objects.filter(username=value).exists():
                raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        """Custom validation for email"""
        if self.instance:  # This is an update
            if StaffAccount.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
                raise serializers.ValidationError("A user with this email already exists.")
        else:  # This is a create
            if StaffAccount.objects.filter(email=value).exists():
                raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_number(self, value):
        """Custom validation for phone number"""
        if self.instance:  # This is an update
            if StaffAccount.objects.exclude(pk=self.instance.pk).filter(phone_number=value).exists():
                raise serializers.ValidationError("A user with this phone number already exists.")
        else:  # This is a create
            if StaffAccount.objects.filter(phone_number=value).exists():
                raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def create(self, validated_data):
        # Password is required for creation
        if 'password' not in validated_data:
            raise serializers.ValidationError({"password": ["This field is required for user creation."]})
            
        request = self.context.get('request')
        if request and hasattr(request.user, 'center_detail'):
            center_detail = request.user.center_detail
        else:
            center_detail = None
            
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
        # Remove password from validated_data if present - it should be updated via reset_password endpoint
        if 'password' in validated_data:
            validated_data.pop('password')
        
        # Update other fields normally
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

# --- Minimal Serializer (No Change) ---
class MinimalStaffAccountSerializer(serializers.ModelSerializer):     
    class Meta:
        model = StaffAccount
        fields = ['id', 'first_name', 'last_name']

# --- UPDATED PASSWORD SERIALIZERS ---

class AdminPasswordResetSerializer(serializers.Serializer):
    """
    Serializer for an Admin to reset any user's password.
    Requires only the new password and validates it against Django's validators.
    """
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
        # Use Django's built-in password validation system
        try:
            validate_password(value)
        except DjangoValidationError as e:
            # Raise a serializer-friendly validation error
            raise serializers.ValidationError(list(e.messages))
        return value

    def update(self, instance, validated_data):
        # Ensures the password is HASHED correctly
        instance.set_password(validated_data['password'])
        instance.save()
        return instance

class UserPasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for a non-admin user changing their OWN password.
    Requires the old password for verification.
    """
    old_password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'},
        error_messages={
            'required': 'Current password is required.',
            'blank': 'Current password cannot be blank.'
        }
    )
    new_password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'},
        error_messages={
            'required': 'New password is required.',
            'blank': 'New password cannot be blank.'
        }
    )

    def validate_old_password(self, value):
        """
        Validates that the provided old_password matches the user's current password.
        The 'request.user' is passed in via context from the view.
        """
        user = self.context['request'].user
        if not user.check_password(value):
            # This is the error message the user will see.
            raise serializers.ValidationError("Your current password was entered incorrectly.")
        return value

    def validate_new_password(self, value):
        """
        Runs the new password through Django's validators.
        """
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, data):
        """
        Cross-field validation to ensure new password is not the same as the old one.
        """
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError(
                {"new_password": ["New password must be different from the current password."]}
            )
        return data

    def update(self, instance, validated_data):
        # Sets the new HASHED password
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance

# --- Custom Token Serializer (No Change) ---
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        # Add basic user info
        data['is_admin'] = self.user.is_admin
        data['username'] = self.user.username
        data['first_name'] = self.user.first_name
        data['last_name'] = self.user.last_name
        data['id'] = self.user.id

        # Add center details
        center = getattr(self.user, "center_detail", None)
        if center:
            # This will dynamically include subscription from OneToOneField
            center_data = CenterDetailTokenSerializer(center).data
            data["center_detail"] = center_data
        else:
            data["center_detail"] = None

        return data