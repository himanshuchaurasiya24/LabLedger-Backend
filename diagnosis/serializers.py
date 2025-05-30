from .models import *
from rest_framework import serializers

class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        # All fields you want to expose:
        fields = '__all__'
        # Make these read-only:
        read_only_fields = (
            'bill_number',
            'total_amount',
            'incentive_amount',
        )