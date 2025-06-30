from rest_framework import serializers
from authentication.models import StaffAccount
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer



from rest_framework import serializers
from authentication.models import StaffAccount
from center_detail.serializers import CenterDetailSerializer

class StaffAccountSerializer(serializers.ModelSerializer):
    center_detail = CenterDetailSerializer(read_only = True)
    class Meta:
        model = StaffAccount
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'address', 'is_admin','center_detail', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = StaffAccount.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data['phone_number'],
            address=validated_data['address'],
            is_admin=validated_data.get('is_admin', False),
            is_staff=validated_data.get('is_admin', False),
            is_superuser=validated_data.get('is_admin', False)
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
class MinimalStaffAccountSerializer(serializers.ModelSerializer):    
    class Meta:
        model = StaffAccount
        fields = ['id',  'first_name', 'last_name']


class PasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value

    def update(self, instance, validated_data):
        instance.set_password(validated_data['password'])
        instance.save()
        return instance
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['is_admin'] = self.user.is_admin  # or use is_superuser depending on your definition
        data['username']= self.user.username
        data['first_name']= self.user.first_name
        data['last_name']= self.user.last_name
        data['id']= self.user.id
        data['center_detail']= CenterDetailSerializer(self.user.center_detail).data
        return data
