import django_filters
from django.utils.timezone import now, timedelta
from calendar import monthrange

from center_detail.models import CenterDetail
from .models import Doctor, DiagnosisType, Bill, PatientReport, SampleTestReport

# Doctor Filter
class DoctorFilter(django_filters.FilterSet):
    first_name = django_filters.CharFilter(field_name='first_name', lookup_expr='icontains')
    last_name = django_filters.CharFilter(field_name='last_name', lookup_expr='icontains')
    phone_number = django_filters.CharFilter(field_name='phone_number', lookup_expr='iexact')
    address = django_filters.CharFilter(field_name='address', lookup_expr='icontains')
    ultrasound_percentage = django_filters.NumberFilter(field_name='ultrasound_percentage')
    pathology_percentage = django_filters.NumberFilter(field_name='pathology_percentage')
    ecg_percentage = django_filters.NumberFilter(field_name='ecg_percentage')
    xray_percentage = django_filters.NumberFilter(field_name='xray_percentage')
    franchise_lab_percentage = django_filters.NumberFilter(field_name='franchise_lab_percentage')

    class Meta:
        model = Doctor
        fields = ['first_name', 'last_name', 'phone_number', 'address', 
                  'ultrasound_percentage', 'pathology_percentage', 
                  'ecg_percentage', 'xray_percentage', 'franchise_lab_percentage']


# DiagnosisType Filter
class DiagnosisTypeFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    category = django_filters.CharFilter(field_name='category', lookup_expr='iexact')
    price = django_filters.NumberFilter(field_name='price')
    center_detail = django_filters.NumberFilter(field_name='center_detail__id')  # Assuming center_detail is a ForeignKey
    # add more fields if needed

    class Meta:
        model = DiagnosisType
        fields = ['name', 'category', 'price', 'center_detail']


# Bill Filter (with your detailed filters)
class BillFilter(django_filters.FilterSet):
    bill_number = django_filters.CharFilter(field_name='bill_number', lookup_expr='iexact')
    patient_name = django_filters.CharFilter(field_name='patient_name', lookup_expr='icontains')
    patient_age = django_filters.NumberFilter(field_name='patient_age')
    patient_sex = django_filters.CharFilter(field_name='patient_sex', lookup_expr='iexact')
    diagnosis_type = django_filters.NumberFilter(field_name='diagnosis_type__id')
    referred_by_doctor = django_filters.NumberFilter(field_name='referred_by_doctor__id')
    test_done_by = django_filters.NumberFilter(field_name='test_done_by__id')

    # Date of Test
    date_of_test = django_filters.DateFilter(field_name='date_of_test__date', lookup_expr='exact')
    start_date = django_filters.DateFilter(field_name='date_of_test__date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='date_of_test__date', lookup_expr='lte')
    test_year = django_filters.NumberFilter(field_name='date_of_test__year', lookup_expr='exact')
    test_month = django_filters.NumberFilter(field_name='date_of_test__month', lookup_expr='exact')

    # Date of Bill
    date_of_bill = django_filters.DateFilter(field_name='date_of_bill__date', lookup_expr='exact')
    bill_start_date = django_filters.DateFilter(field_name='date_of_bill__date', lookup_expr='gte')
    bill_end_date = django_filters.DateFilter(field_name='date_of_bill__date', lookup_expr='lte')
    bill_year = django_filters.NumberFilter(field_name='date_of_bill__year', lookup_expr='exact')
    bill_month = django_filters.NumberFilter(field_name='date_of_bill__month', lookup_expr='exact')

    bill_status = django_filters.CharFilter(field_name='bill_status', lookup_expr='iexact')
    franchise_name = django_filters.CharFilter(field_name='franchise_name', lookup_expr='icontains')

    total_amount = django_filters.NumberFilter(field_name='total_amount')
    paid_amount = django_filters.NumberFilter(field_name='paid_amount')
    disc_by_center = django_filters.NumberFilter(field_name='disc_by_center')
    disc_by_doctor = django_filters.NumberFilter(field_name='disc_by_doctor')
    incentive_amount = django_filters.NumberFilter(field_name='incentive_amount')

    center_detail = django_filters.NumberFilter(field_name='center_detail__id')

    # Custom date-based filters
    last_month = django_filters.BooleanFilter(method='filter_last_month')
    this_month = django_filters.BooleanFilter(method='filter_this_month')
    last_7_days = django_filters.BooleanFilter(method='filter_last_7_days')

    class Meta:
        model = Bill
        fields = [
            'bill_number', 'patient_name', 'patient_age', 'patient_sex',
            'diagnosis_type', 'referred_by_doctor', 'test_done_by',
            'date_of_test', 'start_date', 'end_date', 'test_year', 'test_month',
            'date_of_bill', 'bill_start_date', 'bill_end_date', 'bill_year', 'bill_month',
            'bill_status', 'franchise_name',
            'total_amount', 'paid_amount', 'disc_by_center',
            'disc_by_doctor', 'incentive_amount', 'center_detail',
            'last_month', 'this_month', 'last_7_days',
        ]

    def filter_last_month(self, queryset, name, value):
        if value:
            today = now().date()
            year = today.year
            month = today.month - 1 or 12
            if month == 12:
                year -= 1
            first_day = f"{year}-{month:02d}-01"
            last_day = f"{year}-{month:02d}-{monthrange(year, month)[1]}"
            return queryset.filter(date_of_test__date__range=[first_day, last_day])
        return queryset

    def filter_this_month(self, queryset, name, value):
        if value:
            today = now().date()
            return queryset.filter(date_of_test__year=today.year, date_of_test__month=today.month)
        return queryset

    def filter_last_7_days(self, queryset, name, value):
        if value:
            cutoff = now().date() - timedelta(days=7)
            return queryset.filter(date_of_test__date__gte=cutoff)
        return queryset

# PatientReport Filter
class PatientReportFilter(django_filters.FilterSet):
    patient_name = django_filters.CharFilter(field_name='patient_name', lookup_expr='icontains')
    report_type = django_filters.CharFilter(field_name='report_type', lookup_expr='icontains')
    start_date = django_filters.DateFilter(field_name='date_of_report', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='date_of_report', lookup_expr='lte')

    class Meta:
        model = PatientReport
        fields = ['patient_name', 'report_type', 'start_date', 'end_date']

class SampleTestReportFilter(django_filters.FilterSet):
    diagnosis_type = django_filters.CharFilter(field_name="diagnosis_type", lookup_expr="iexact")
    diagnosis_name = django_filters.CharFilter(field_name="diagnosis_name", lookup_expr="icontains")
    center_detail = django_filters.ModelChoiceFilter(queryset=CenterDetail.objects.all())

    class Meta:
        model = SampleTestReport
        fields = ["diagnosis_type", "diagnosis_name", "center_detail"]
