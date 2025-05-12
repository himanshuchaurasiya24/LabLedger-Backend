from rest_framework import serializers
from authentication.models import StaffAccount



from rest_framework import serializers
from authentication.models import StaffAccount

class StaffAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffAccount
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'address', 'is_admin','center_name', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = StaffAccount.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data['phone_number'],
            address=validated_data['address'],
            center_name=validated_data['center_name'],
            is_admin=validated_data.get('is_admin', False),
            is_staff=validated_data.get('is_admin', False),
            is_superuser=validated_data.get('is_admin', False)
        )
        user.set_password(validated_data['password'])
        user.save()
        return user