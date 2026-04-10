import django_filters
from django.utils.timezone import now, timedelta
from calendar import monthrange
from center_detail.models import CenterDetail

class CenterDetailFilter(django_filters.FilterSet):
    center_name = django_filters.CharFilter(field_name='center_name', lookup_expr='icontains')
    address = django_filters.CharFilter(field_name='address', lookup_expr='icontains')
    owner_phone = django_filters.CharFilter(field_name='owner_phone', lookup_expr='iexact')
    owner_name = django_filters.CharFilter(field_name='owner_name', lookup_expr='icontains')

    class Meta:
        model = CenterDetail
        fields = ['center_name', 'address', 'owner_phone', 'owner_name']