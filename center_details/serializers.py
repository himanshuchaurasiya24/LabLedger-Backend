
from rest_framework import serializers

from center_details.models import CenterDetail



class CenterDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CenterDetail
        fields = "__all__"