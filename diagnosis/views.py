from datetime import datetime, timedelta, date
from calendar import monthrange
from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Concat, TruncDate
from django.utils.timezone import now, make_aware, get_default_timezone
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Bill
from .serializers import BillSerializer
from .filters import BillFilter
from center_detail.permissions import IsSubscriptionActive
from .models import *
from .serializers import *
from .filters import *
# --- ADDED: Import your new pagination class ---
from .pagination import StandardResultsSetPagination 
from .models import Bill
from .serializers import BillSerializer
from .filters import BillFilter

class CenterDetailFilterMixin:
    def get_queryset(self):
        model = self.queryset.model
        if self.request.user.center_detail is None:
            return model.objects.none()
        return model.objects.filter(center_detail=self.request.user.center_detail)

    @property
    def request_detail(self):
        return self.request.user.center_detail
    

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin

class DoctorViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = DoctorFilter
    search_fields = ['first_name', 'last_name', 'phone_number']
    
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('-first_name')
        
    def get_permissions(self):
        # PERMISSION ADDED
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive, IsAdminUser]
        else:  # list, retrieve
            permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]
        return [perm() for perm in permission_classes]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])
        return Response(serializer.data)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)

class DiagnosisTypeViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = DiagnosisType.objects.all()
    serializer_class = DiagnosisTypeSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = DiagnosisTypeFilter
    search_fields = ['name', 'description']
    
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('-name')
        
    def get_permissions(self):
        # PERMISSION ADDED
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive, IsAdminUser]
        else:  # list, retrieve
            permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]
        return [perm() for perm in permission_classes]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])
        return Response(serializer.data)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)


class FranchiseNameViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    serializer_class = FranchiseNameSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['franchise_name', 'address', 'phone_number']
    
    def get_queryset(self):
        user_center = self.request.user.center_detail
        return FranchiseName.objects.filter(center_detail=user_center).order_by('-franchise_name')

    def get_permissions(self):
        # PERMISSION ADDED
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive, IsAdminUser]
        else:  # list, retrieve
            permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]
        return [perm() for perm in permission_classes]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.center_detail != request.user.center_detail:
            return Response(
                {'detail': 'You do not have permission to access this franchise.'},
                status=403
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_update(self, serializer):
        instance = self.get_object()
        user = self.request.user
        if instance.center_detail != user.center_detail:
            raise ValidationError("You cannot update franchise from another center.")
        serializer.save(center_detail=user.center_detail)

class ReferralStatsViewSet(viewsets.ViewSet):
    # PERMISSION ADDED
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]

    def list(self, request):
        # TIMEZONE CORRECTION
        tz = get_default_timezone()
        today = now().astimezone(tz).date()

        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        start_of_month = today.replace(day=1)
        end_of_month_day = monthrange(today.year, today.month)[1]
        end_of_month = today.replace(day=end_of_month_day)

        start_of_year = today.replace(month=1, day=1)
        end_of_year = today.replace(month=12, day=31)

        doctor_id = request.query_params.get("referred_by_doctor")

        def bills_in_range(start_date, end_date):
            start_dt = make_aware(datetime.combine(start_date, datetime.min.time()), timezone=tz)
            end_dt = make_aware(datetime.combine(end_date, datetime.max.time()), timezone=tz)
            qs = Bill.objects.filter(center_detail=request.user.center_detail, date_of_bill__range=(start_dt, end_dt))
            if doctor_id:
                qs = qs.filter(referred_by_doctor_id=doctor_id)
            return qs

        def get_referral_stats(qs):
            return (
                qs.values("referred_by_doctor")
                .annotate(
                    doctor_full_name=Concat("referred_by_doctor__first_name", Value(" "), "referred_by_doctor__last_name"),
                    total=Count("id"),
                    ultrasound=Count("id", filter=Q(diagnosis_type__category="Ultrasound")),
                    ecg=Count("id", filter=Q(diagnosis_type__category="ECG")),
                    xray=Count("id", filter=Q(diagnosis_type__category="X-Ray")),
                    pathology=Count("id", filter=Q(diagnosis_type__category="Pathology")),
                    franchise_lab=Count("id", filter=Q(diagnosis_type__category="Franchise Lab")),
                    incentive_amount=Sum("incentive_amount"),
                )
                .values("referred_by_doctor__id", "doctor_full_name", "total", "ultrasound", "ecg", "xray", "pathology", "franchise_lab", "incentive_amount")
                .order_by("-total")
            )

        all_time_qs = Bill.objects.filter(center_detail=request.user.center_detail)
        if doctor_id:
            all_time_qs = all_time_qs.filter(referred_by_doctor_id=doctor_id)

        data = {
            "this_week": get_referral_stats(bills_in_range(start_of_week, end_of_week)),
            "this_month": get_referral_stats(bills_in_range(start_of_month, end_of_month)),
            "this_year": get_referral_stats(bills_in_range(start_of_year, end_of_year)),
            "all_time": get_referral_stats(all_time_qs),
        }
        return Response(data)

class BillChartStatsViewSet(viewsets.ViewSet):
    # PERMISSION ADDED
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]

    def list(self, request):
        tz = get_default_timezone()
        today = now().astimezone(tz).date()
        doctor_id = request.query_params.get("referred_by_doctor")

        def get_chart_stats(start_date, end_date):
            start_dt = make_aware(datetime.combine(start_date, datetime.min.time()), tz)
            end_dt = make_aware(datetime.combine(end_date, datetime.max.time()), tz)
            
            qs = Bill.objects.filter(center_detail=request.user.center_detail, date_of_bill__range=(start_dt, end_dt))
            if doctor_id:
                qs = qs.filter(referred_by_doctor_id=doctor_id)

            return (
                qs.annotate(day=TruncDate("date_of_bill"))
                .values("day")
                .annotate(
                    total=Count("id"),
                    ultrasound=Count("id", filter=Q(diagnosis_type__category="Ultrasound")),
                    ecg=Count("id", filter=Q(diagnosis_type__category="ECG")),
                    xray=Count("id", filter=Q(diagnosis_type__category="X-Ray")),
                    pathology=Count("id", filter=Q(diagnosis_type__category="Pathology")),
                    franchise_lab=Count("id", filter=Q(diagnosis_type__category="Franchise Lab")),
                )
                .order_by("day")
            )

        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        start_of_month = today.replace(day=1)
        end_of_month_day = monthrange(today.year, today.month)[1]
        end_of_month = today.replace(day=end_of_month_day)
        start_of_year = today.replace(month=1, day=1)
        end_of_year = today.replace(month=12, day=31)

        all_time_qs = Bill.objects.filter(center_detail=request.user.center_detail)
        if doctor_id:
            all_time_qs = all_time_qs.filter(referred_by_doctor_id=doctor_id)
        
        all_time_stats = (
            all_time_qs.annotate(day=TruncDate("date_of_bill"))
            .values("day")
            .annotate(
                total=Count("id"),
                ultrasound=Count("id", filter=Q(diagnosis_type__category="Ultrasound")),
                ecg=Count("id", filter=Q(diagnosis_type__category="ECG")),
                xray=Count("id", filter=Q(diagnosis_type__category="X-Ray")),
                pathology=Count("id", filter=Q(diagnosis_type__category="Pathology")),
                franchise_lab=Count("id", filter=Q(diagnosis_type__category="Franchise Lab")),
            )
            .order_by("day")
        )

        data = {
            "this_week": get_chart_stats(start_of_week, end_of_week),
            "this_month": get_chart_stats(start_of_month, end_of_month),
            "this_year": get_chart_stats(start_of_year, end_of_year),
            "all_time": all_time_stats,
        }
        return Response(data)

class BillGrowthStatsView(APIView):
    # PERMISSION ADDED
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]

    def get_quarter_range(self, year, quarter):
        if quarter == 1: return date(year, 1, 1), date(year, 3, 31)
        elif quarter == 2: return date(year, 4, 1), date(year, 6, 30)
        elif quarter == 3: return date(year, 7, 1), date(year, 9, 30)
        else: return date(year, 10, 1), date(year, 12, 31)

    def get_month_range(self, year, month):
        first_day = date(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = date(year, month, last_day_num)
        return first_day, last_day

    def aggregate(self, qs):
        total_bills = qs.count()
        diagnosis_counts = qs.values('diagnosis_type__category').annotate(count=Count('id'))
        return {
            "total_bills": total_bills,
            "diagnosis_counts": {item['diagnosis_type__category']: item['count'] for item in diagnosis_counts}
        }

    def get_filtered_queryset(self, start_date, end_date, base_qs):
        return base_qs.filter(date_of_bill__date__range=(start_date, end_date))

    def get(self, request, format=None):
        # TIMEZONE CORRECTION
        tz = get_default_timezone()
        today = now().astimezone(tz).date()
        base_qs = Bill.objects.filter(center_detail=request.user.center_detail)

        # Current vs Previous Month
        first_curr_month, last_curr_month = self.get_month_range(today.year, today.month)
        prev_month_date = first_curr_month - timedelta(days=1)
        first_prev_month, last_prev_month = self.get_month_range(prev_month_date.year, prev_month_date.month)

        # Current vs Previous Year
        first_curr_year, last_curr_year = date(today.year, 1, 1), date(today.year, 12, 31)
        first_prev_year, last_prev_year = date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)

        # Current vs Previous Quarter
        current_quarter = (today.month - 1) // 3 + 1
        first_curr_quarter, last_curr_quarter = self.get_quarter_range(today.year, current_quarter)
        prev_quarter_year, prev_quarter = (today.year - 1, 4) if current_quarter == 1 else (today.year, current_quarter - 1)
        first_prev_quarter, last_prev_quarter = self.get_quarter_range(prev_quarter_year, prev_quarter)

        data = {
            "current_month": self.aggregate(self.get_filtered_queryset(first_curr_month, last_curr_month, base_qs)),
            "previous_month": self.aggregate(self.get_filtered_queryset(first_prev_month, last_prev_month, base_qs)),
            "current_year": self.aggregate(self.get_filtered_queryset(first_curr_year, last_curr_year, base_qs)),
            "previous_year": self.aggregate(self.get_filtered_queryset(first_prev_year, last_prev_year, base_qs)),
            "current_quarter": self.aggregate(self.get_filtered_queryset(first_curr_quarter, last_curr_quarter, base_qs)),
            "previous_quarter": self.aggregate(self.get_filtered_queryset(first_prev_quarter, last_prev_quarter, base_qs)),
        }
        return Response(data)


class BillViewset(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]
    
    # --- ADDED: This enables fast, scalable pagination ---
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = BillFilter
    search_fields = [
        "bill_number",
        "patient_name",
        "diagnosis_type__name",
        "diagnosis_type__category",
        "referred_by_doctor__first_name",
        "referred_by_doctor__last_name",
        "franchise_name",
        "bill_status",
    ]

    # --- REMOVED: The entire custom `def list(self, ...)` method is GONE. ---
    # DRF's default list method will now handle filtering, searching, and pagination.

    def get_queryset(self):
        qs = super().get_queryset()
        # Ensure consistent ordering for pagination
        return qs.order_by("-id")

    @action(detail=False, methods=["get"], url_path="franchise-names")
    def franchise_names(self, request):
        franchises = (
            self.get_queryset()
            .exclude(franchise_name__isnull=True)
            .exclude(franchise_name__exact="")
            .values_list("franchise_name", flat=True)
            .distinct()
        )
        return Response(franchises)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(test_done_by=user, center_detail=user.center_detail)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={"request": request})
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])
        return Response(serializer.data)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(test_done_by=user, center_detail=user.center_detail)

class PatientReportViewset(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = PatientReport.objects.all()
    serializer_class = PatientReportSerializer
    authentication_classes = [JWTAuthentication]
    # PERMISSION ADDED
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = PatientReportFilter
    search_fields = ['patient_name', 'report_title']

    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)
        
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])
        return Response(serializer.data)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)

class SampleTestReportViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = SampleTestReport.objects.all()
    serializer_class = SampleTestReportSerializer
    authentication_classes = [JWTAuthentication]
    # PERMISSION ADDED
    permission_classes = [permissions.IsAuthenticated, IsSubscriptionActive]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = SampleTestReportFilter
    search_fields = ["diagnosis_type", "diagnosis_name", "center_detail__name"]
    
    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)
        
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])
        return Response(serializer.data)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)