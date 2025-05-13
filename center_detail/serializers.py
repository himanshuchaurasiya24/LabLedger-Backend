from .models import CenterDetail
from rest_framework import serializers

class CenterDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CenterDetail
        fields = "__all__"