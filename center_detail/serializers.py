from .models import CenterDetail
from rest_framework import serializers

class CenterDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CenterDetail
        fields = '__all__'
class MinimalCenterDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CenterDetail
        fields = ['id','center_name', 'address']


