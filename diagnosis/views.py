from datetime import datetime, timedelta, date
from calendar import monthrange
from itertools import groupby
from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Concat, TruncDate
from django.utils.timezone import now, make_aware, get_default_timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from center_detail.permissions import IsSubscriptionActive, IsUserNotLocked
from .models import *
from .serializers import *
from .filters import *
from .pagination import StandardResultsSetPagination
from .models import AuditLog


def audit_log(user, action, model_name, object_id='', details='', request=None):
    """
    Helper to create an AuditLog entry.
    """
    ip_address = None
    user_agent = ''
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else None,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def _safe_audit_log(user, action, model_name, object_id='', details='', request=None):
    """
    Best-effort audit logger so business APIs are not blocked if logging fails.
    """
    try:
        audit_log(
            user=user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            details=details,
            request=request,
        )
    except Exception:
        pass


class CenterDetailFilterMixin:
    """
    A mixin that filters querysets based on the request.user.center_detail.
    """
    def get_queryset(self):
        model = self.queryset.model
        user = self.request.user
        if not hasattr(user, 'center_detail') or user.center_detail is None:
            return model.objects.none()
        return model.objects.filter(center_detail=user.center_detail)

    @property
    def request_detail(self):
        return self.request.user.center_detail

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin

# --- Model ViewSets ---
class DoctorViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = DoctorFilter
    search_fields = ['first_name', 'last_name', 'phone_number']

    def get_queryset(self):
        from django.db.models.functions import Lower
        return super().get_queryset().order_by(Lower('first_name'))

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive, IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]
        return [perm() for perm in permission_classes]

    def perform_create(self, serializer):
        instance = serializer.save(center_detail=self.request.user.center_detail)
        _safe_audit_log(
            user=self.request.user,
            action='CREATE',
            model_name='Doctor',
            object_id=instance.pk,
            details=f"Created doctor {instance.first_name} {instance.last_name}".strip(),
            request=self.request,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])
        return Response(serializer.data)

    def perform_update(self, serializer):
        # ✅ REFINEMENT: Ensure the object being updated belongs to the user's center.
        if serializer.instance.center_detail != self.request.user.center_detail:
            raise PermissionDenied("You do not have permission to edit this doctor.")
        instance = serializer.save()
        _safe_audit_log(
            user=self.request.user,
            action='UPDATE',
            model_name='Doctor',
            object_id=instance.pk,
            details=f"Updated doctor {instance.first_name} {instance.last_name}".strip(),
            request=self.request,
        )

    def perform_destroy(self, instance):
        doctor_name = f"{instance.first_name} {instance.last_name}".strip()
        doctor_id = instance.pk
        super().perform_destroy(instance)
        _safe_audit_log(
            user=self.request.user,
            action='DELETE',
            model_name='Doctor',
            object_id=doctor_id,
            details=f"Deleted doctor {doctor_name}".strip(),
            request=self.request,
        )

class DiagnosisTypeViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = DiagnosisType.objects.all()
    serializer_class = DiagnosisTypeSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = DiagnosisTypeFilter
    search_fields = ['name', 'category__name']

    def get_queryset(self):
        return super().get_queryset().order_by('name')

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive, IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]
        return [perm() for perm in permission_classes]
    
    # ✅ REFACTORED: Handles assigning the center_detail automatically.
    def perform_create(self, serializer):
        instance = serializer.save(center_detail=self.request_detail)
        _safe_audit_log(
            user=self.request.user,
            action='CREATE',
            model_name='DiagnosisType',
            object_id=instance.pk,
            details=f"Created diagnosis type {instance.name}",
            request=self.request,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])
        return Response(serializer.data)

    def perform_update(self, serializer):
        instance = serializer.save(center_detail=self.request_detail)
        _safe_audit_log(
            user=self.request.user,
            action='UPDATE',
            model_name='DiagnosisType',
            object_id=instance.pk,
            details=f"Updated diagnosis type {instance.name}",
            request=self.request,
        )

    def perform_destroy(self, instance):
        diagnosis_name = instance.name
        diagnosis_type_id = instance.pk
        super().perform_destroy(instance)
        _safe_audit_log(
            user=self.request.user,
            action='DELETE',
            model_name='DiagnosisType',
            object_id=diagnosis_type_id,
            details=f"Deleted diagnosis type {diagnosis_name}",
            request=self.request,
        )

class FranchiseNameViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = FranchiseName.objects.all()
    serializer_class = FranchiseNameSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['franchise_name', 'address', 'phone_number']

    def get_queryset(self):
        return super().get_queryset().order_by('franchise_name')

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive, IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]
        return [perm() for perm in permission_classes]
    
    def perform_create(self, serializer):
        """
        Automatically associate the new FranchiseName with the logged-in user's center.
        """
        instance = serializer.save(center_detail=self.request.user.center_detail)
        _safe_audit_log(
            user=self.request.user,
            action='CREATE',
            model_name='FranchiseName',
            object_id=instance.pk,
            details=f"Created franchise {instance.franchise_name}",
            request=self.request,
        )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_update(self, serializer):
        instance = serializer.save(center_detail=self.request_detail)
        _safe_audit_log(
            user=self.request.user,
            action='UPDATE',
            model_name='FranchiseName',
            object_id=instance.pk,
            details=f"Updated franchise {instance.franchise_name}",
            request=self.request,
        )

    def perform_destroy(self, instance):
        franchise_name = instance.franchise_name
        franchise_id = instance.pk
        super().perform_destroy(instance)
        _safe_audit_log(
            user=self.request.user,
            action='DELETE',
            model_name='FranchiseName',
            object_id=franchise_id,
            details=f"Deleted franchise {franchise_name}",
            request=self.request,
        )

class BillViewset(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]
    
    def get_permissions(self):
        """
        Allow non-admin users to create, list, retrieve.
        Require admin for update, partial_update, destroy.
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive, IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]
        return [perm() for perm in permission_classes]
    
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = BillFilter
    search_fields = [
        "bill_number",
        "patient_name",
        "bill_diagnosis_types__diagnosis_type__name",
        "bill_diagnosis_types__diagnosis_type__category__name",
        "referred_by_doctor__first_name",
        "referred_by_doctor__last_name",
        "franchise_name__franchise_name", # ✅ Updated for ForeignKey relationship
        "bill_status",
    ]

    def get_queryset(self):
        return super().get_queryset().order_by("-date_of_bill", "-id")

    @action(detail=False, methods=["get"], url_path="franchise-names")
    def franchise_names(self, request):
        franchises = FranchiseName.objects.filter(center_detail=self.request_detail)
        serializer = FranchiseNameSerializer(franchises, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        instance = serializer.save()
        _safe_audit_log(
            user=self.request.user,
            action='CREATE',
            model_name='Bill',
            object_id=instance.pk,
            details=f"Created bill {instance.bill_number}",
            request=self.request,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={"request": request})
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])
        return Response(serializer.data)

    def perform_update(self, serializer):
        instance = serializer.save()
        _safe_audit_log(
            user=self.request.user,
            action='UPDATE',
            model_name='Bill',
            object_id=instance.pk,
            details=f"Updated bill {instance.bill_number}",
            request=self.request,
        )

    def perform_destroy(self, instance):
        bill_number = instance.bill_number
        bill_id = instance.pk
        super().perform_destroy(instance)
        _safe_audit_log(
            user=self.request.user,
            action='DELETE',
            model_name='Bill',
            object_id=bill_id,
            details=f"Deleted bill {bill_number}",
            request=self.request,
        )

class PatientReportViewset(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = PatientReport.objects.all()
    serializer_class = PatientReportSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]
    
    def get_permissions(self):
        """
        Allow non-admin users to create, list, retrieve.
        Require admin for update, partial_update, destroy.
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive, IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]
        return [perm() for perm in permission_classes]
    
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = PatientReportFilter
    search_fields = ['bill__patient_name', 'bill__bill_number']

    def get_queryset(self):
        """
        Overrides the default queryset to filter by the user's center and
        optionally by a specific bill ID passed in the query parameters.
        """
        queryset = super().get_queryset()
        bill_id = self.request.query_params.get('bill')
        if bill_id is not None:
            queryset = queryset.filter(bill__id=bill_id)        
        return queryset.order_by('-id')

    def perform_create(self, serializer):
        """Assigns the center_detail automatically during creation."""
        instance = serializer.save(center_detail=self.request.user.center_detail)
        _safe_audit_log(
            user=self.request.user,
            action='CREATE',
            model_name='PatientReport',
            object_id=instance.pk,
            details=f"Created patient report for bill {instance.bill.bill_number}",
            request=self.request,
        )
        
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])
        return Response(serializer.data)

    def perform_update(self, serializer):
        """Assigns the center_detail automatically during an update."""
        instance = serializer.save(center_detail=self.request.user.center_detail)
        _safe_audit_log(
            user=self.request.user,
            action='UPDATE',
            model_name='PatientReport',
            object_id=instance.pk,
            details=f"Updated patient report for bill {instance.bill.bill_number}",
            request=self.request,
        )

    def perform_destroy(self, instance):
        report_id = instance.pk
        bill_number = instance.bill.bill_number
        super().perform_destroy(instance)
        _safe_audit_log(
            user=self.request.user,
            action='DELETE',
            model_name='PatientReport',
            object_id=report_id,
            details=f"Deleted patient report for bill {bill_number}",
            request=self.request,
        )

class SampleTestReportViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = SampleTestReport.objects.all()
    serializer_class = SampleTestReportSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = SampleTestReportFilter
    search_fields = ["category", "diagnosis_name"]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive, IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]
        return [perm() for perm in permission_classes]

    def get_queryset(self):
        return super().get_queryset().order_by('-id')
    
    def perform_create(self, serializer):
        instance = serializer.save(center_detail=self.request_detail)
        _safe_audit_log(
            user=self.request.user,
            action='CREATE',
            model_name='SampleTestReport',
            object_id=instance.pk,
            details=f"Created sample report {instance.diagnosis_name}",
            request=self.request,
        )
        
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])
        return Response(serializer.data)

    def perform_update(self, serializer):
        instance = serializer.save(center_detail=self.request_detail)
        _safe_audit_log(
            user=self.request.user,
            action='UPDATE',
            model_name='SampleTestReport',
            object_id=instance.pk,
            details=f"Updated sample report {instance.diagnosis_name}",
            request=self.request,
        )

    def perform_destroy(self, instance):
        diagnosis_name = instance.diagnosis_name
        report_id = instance.pk
        super().perform_destroy(instance)
        _safe_audit_log(
            user=self.request.user,
            action='DELETE',
            model_name='SampleTestReport',
            object_id=report_id,
            details=f"Deleted sample report {diagnosis_name}",
            request=self.request,
        )
class ReferralStatsViewSet(viewsets.ViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]

    def list(self, request):
        tz = get_default_timezone()
        today = now().astimezone(tz).date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        start_of_month = today.replace(day=1)
        _, end_of_month_day = monthrange(today.year, today.month)
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
            grouped = list(
                qs.values("referred_by_doctor")
                .annotate(
                    doctor_full_name=Concat("referred_by_doctor__first_name", Value(" "), "referred_by_doctor__last_name"),
                    total=Count("id", distinct=True),
                    ultrasound=Count("id", filter=Q(bill_diagnosis_types__diagnosis_type__category__name="Ultrasound"), distinct=True),
                    ecg=Count("id", filter=Q(bill_diagnosis_types__diagnosis_type__category__name="ECG"), distinct=True),
                    xray=Count("id", filter=Q(bill_diagnosis_types__diagnosis_type__category__name="X-Ray"), distinct=True),
                    pathology=Count("id", filter=Q(bill_diagnosis_types__diagnosis_type__category__name="Pathology"), distinct=True),
                    franchise_lab=Count("id", filter=Q(bill_diagnosis_types__diagnosis_type__category__is_franchise_lab=True), distinct=True),
                )
                .values("referred_by_doctor__id", "doctor_full_name", "total", "ultrasound", "ecg", "xray", "pathology", "franchise_lab")
                .order_by("-total")
            )

            incentive_map = {
                row["referred_by_doctor"]: row["total_incentive"] or 0
                for row in qs.values("referred_by_doctor").annotate(total_incentive=Sum("incentive_amount"))
            }

            for row in grouped:
                row["incentive_amount"] = incentive_map.get(row["referred_by_doctor__id"], 0)

            return grouped

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
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]

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
                    total=Count("id", distinct=True),
                    ultrasound=Count("id", filter=Q(bill_diagnosis_types__diagnosis_type__category__name="Ultrasound"), distinct=True),
                    ecg=Count("id", filter=Q(bill_diagnosis_types__diagnosis_type__category__name="ECG"), distinct=True),
                    xray=Count("id", filter=Q(bill_diagnosis_types__diagnosis_type__category__name="X-Ray"), distinct=True),
                    pathology=Count("id", filter=Q(bill_diagnosis_types__diagnosis_type__category__name="Pathology"), distinct=True),
                    franchise_lab=Count("id", filter=Q(bill_diagnosis_types__diagnosis_type__category__is_franchise_lab=True), distinct=True),
                )
                .order_by("day")
            )

        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        start_of_month = today.replace(day=1)
        _, end_of_month_day = monthrange(today.year, today.month)
        end_of_month = today.replace(day=end_of_month_day)
        start_of_year = today.replace(month=1, day=1)
        end_of_year = today.replace(month=12, day=31)
        
        data = {
            "this_week": get_chart_stats(start_of_week, end_of_week),
            "this_month": get_chart_stats(start_of_month, end_of_month),
            "this_year": get_chart_stats(start_of_year, end_of_year),
        }
        return Response(data)
class DoctorBillGrowthStatsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]

    def get_quarter_range(self, year, quarter):
        if quarter == 1: return date(year, 1, 1), date(year, 3, 31)
        elif quarter == 2: return date(year, 4, 1), date(year, 6, 30)
        elif quarter == 3: return date(year, 7, 1), date(year, 9, 30)
        else: return date(year, 10, 1), date(year, 12, 31)

    def get_month_range(self, year, month):
        first_day = date(year, month, 1)
        _, last_day_num = monthrange(year, month)
        last_day = date(year, month, last_day_num)
        return first_day, last_day

    def aggregate(self, qs):
        # This is the updated method
        aggregates = qs.aggregate(
            total_bills=Count('id'),
            total_incentive=Sum('incentive_amount')
        )
        diagnosis_counts = qs.values('bill_diagnosis_types__diagnosis_type__category__name').annotate(count=Count('id', distinct=True))

        return {
            "total_bills": aggregates['total_bills'] or 0,
            "total_incentive": aggregates['total_incentive'] or 0,
            # This line was added to include the breakdown in the response
            "diagnosis_counts": {
                item['bill_diagnosis_types__diagnosis_type__category__name']: item['count']
                for item in diagnosis_counts if item['bill_diagnosis_types__diagnosis_type__category__name']
            }
        }

    def get_filtered_queryset(self, start_date, end_date, base_qs):
        return base_qs.filter(date_of_bill__date__range=(start_date, end_date))

    def get(self, request, doctor_id, format=None):
        today = now().date()
        base_qs = Bill.objects.filter(
            center_detail=request.user.center_detail,
            referred_by_doctor_id=doctor_id
        )
        first_curr_month, last_curr_month = self.get_month_range(today.year, today.month)
        prev_month_date = first_curr_month - timedelta(days=1)
        first_prev_month, last_prev_month = self.get_month_range(prev_month_date.year, prev_month_date.month)
        first_curr_year, last_curr_year = date(today.year, 1, 1), date(today.year, 12, 31)
        first_prev_year, last_prev_year = date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
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

class BillGrowthStatsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]

    def get_quarter_range(self, year, quarter):
        if quarter == 1: return date(year, 1, 1), date(year, 3, 31)
        elif quarter == 2: return date(year, 4, 1), date(year, 6, 30)
        elif quarter == 3: return date(year, 7, 1), date(year, 9, 30)
        else: return date(year, 10, 1), date(year, 12, 31)

    def get_month_range(self, year, month):
        first_day = date(year, month, 1)
        _, last_day_num = monthrange(year, month)
        last_day = date(year, month, last_day_num)
        return first_day, last_day

    def aggregate(self, qs):
        total_bills = qs.values('id').distinct().count()
        diagnosis_counts = qs.values('bill_diagnosis_types__diagnosis_type__category__name').annotate(count=Count('id', distinct=True))
        return {
            "total_bills": total_bills,
            "diagnosis_counts": {
                item['bill_diagnosis_types__diagnosis_type__category__name']: item['count']
                for item in diagnosis_counts if item['bill_diagnosis_types__diagnosis_type__category__name']
            }
        }

    def get_filtered_queryset(self, start_date, end_date, base_qs):
        return base_qs.filter(date_of_bill__date__range=(start_date, end_date))

    def get(self, request, format=None):
        today = now().date()
        base_qs = Bill.objects.filter(center_detail=request.user.center_detail)
        first_curr_month, last_curr_month = self.get_month_range(today.year, today.month)
        prev_month_date = first_curr_month - timedelta(days=1)
        first_prev_month, last_prev_month = self.get_month_range(prev_month_date.year, prev_month_date.month)
        first_curr_year, last_curr_year = date(today.year, 1, 1), date(today.year, 12, 31)
        first_prev_year, last_prev_year = date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
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

class DoctorIncentiveStatsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]

    def get_date_ranges(self, today):
        """Helper to calculate all required start and end dates."""
        # Month Ranges
        first_curr_month = today.replace(day=1)
        _, last_day_num = monthrange(today.year, today.month)
        last_curr_month = today.replace(day=last_day_num)
        
        last_prev_month = first_curr_month - timedelta(days=1)
        first_prev_month = last_prev_month.replace(day=1)

        # Quarter Ranges
        current_quarter = (today.month - 1) // 3 + 1
        if current_quarter == 1:
            first_curr_quarter, last_curr_quarter = date(today.year, 1, 1), date(today.year, 3, 31)
            first_prev_quarter, last_prev_quarter = date(today.year - 1, 10, 1), date(today.year - 1, 12, 31)
        elif current_quarter == 2:
            first_curr_quarter, last_curr_quarter = date(today.year, 4, 1), date(today.year, 6, 30)
            first_prev_quarter, last_prev_quarter = date(today.year, 1, 1), date(today.year, 3, 31)
        elif current_quarter == 3:
            first_curr_quarter, last_curr_quarter = date(today.year, 7, 1), date(today.year, 9, 30)
            first_prev_quarter, last_prev_quarter = date(today.year, 4, 1), date(today.year, 6, 30)
        else: # Quarter 4
            first_curr_quarter, last_curr_quarter = date(today.year, 10, 1), date(today.year, 12, 31)
            first_prev_quarter, last_prev_quarter = date(today.year, 7, 1), date(today.year, 9, 30)
            
        # Year Ranges
        first_curr_year, last_curr_year = date(today.year, 1, 1), date(today.year, 12, 31)
        first_prev_year, last_prev_year = date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)

        return {
            "current_month": (first_curr_month, last_curr_month),
            "previous_month": (first_prev_month, last_prev_month),
            "current_quarter": (first_curr_quarter, last_curr_quarter),
            "previous_quarter": (first_prev_quarter, last_prev_quarter),
            "current_year": (first_curr_year, last_curr_year),
            "previous_year": (first_prev_year, last_prev_year),
        }

    def aggregate_incentives(self, qs):
        """Helper to perform the incentive aggregation on a queryset."""
        total_incentive_data = qs.aggregate(total=Sum('incentive_amount', default=0))
        total_bills = qs.values('id').distinct().count()
        
        breakdown_data = qs.values('bill_diagnosis_types__diagnosis_type__category__name').annotate(
            category_total=Sum('incentive_amount')
        ).order_by()

        return {
            "total_bills": total_bills,
            "total_incentive": total_incentive_data['total'] or 0,
            "diagnosis_counts": {
                item['bill_diagnosis_types__diagnosis_type__category__name']: item['category_total']
                for item in breakdown_data if item['bill_diagnosis_types__diagnosis_type__category__name']
            }
        }

    def get(self, request, doctor_id, format=None):
        # 1. Start with the base queryset
        base_qs = Bill.objects.filter(
            center_detail=request.user.center_detail,
            referred_by_doctor_id=doctor_id
        )

        # 2. Apply optional filters from query parameters
        franchise_id = request.query_params.get('franchise_name_id')
        diagnosis_type_id = request.query_params.get('diagnosis_type_id')
        bill_statuses = request.query_params.getlist('bill_status')

        if franchise_id:
            base_qs = base_qs.filter(franchise_name_id=franchise_id)
        if diagnosis_type_id:
            base_qs = base_qs.filter(diagnosis_types__id=diagnosis_type_id).distinct()
        if bill_statuses:
            status_query = Q()
            for status in bill_statuses:
                status_query |= Q(bill_status__iexact=status)
            base_qs = base_qs.filter(status_query)

        # 3. Get all date ranges and calculate stats for each period
        today = now().date()
        # ✅ FIXED THE TYPO HERE (get_date_ranges is now plural)
        date_ranges = self.get_date_ranges(today)
        
        response_data = {}
        for period, (start_date, end_date) in date_ranges.items():
            period_qs = base_qs.filter(date_of_bill__date__range=(start_date, end_date))
            response_data[period] = self.aggregate_incentives(period_qs)
            
        return Response(response_data)

class FlexibleIncentiveReportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive, IsAdminUser]

    def get(self, request, format=None):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        if start_date_str and end_date_str:
            try:
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str)
            except ValueError:
                return Response({"error": "Invalid date format. Please use YYYY-MM-DD."}, status=400)
        else:
            today = now().date()
            start_date = today.replace(day=1)
            end_date = today

        # 2. Build the base queryset with initial filters
        base_qs = Bill.objects.filter(
            center_detail=request.user.center_detail,
            date_of_bill__date__range=(start_date, end_date)
        )

        # 3. Apply all flexible, multi-value filters from query parameters
        doctor_ids = request.query_params.getlist('doctor_id')
        franchise_ids = request.query_params.getlist('franchise_id')
        diagnosis_type_ids = request.query_params.getlist('diagnosis_type_id')
        bill_statuses = request.query_params.getlist('bill_status')

        if doctor_ids:
            base_qs = base_qs.filter(referred_by_doctor_id__in=doctor_ids)
        
        if franchise_ids:
            base_qs = base_qs.filter(franchise_name_id__in=franchise_ids)
            
        if diagnosis_type_ids:
            base_qs = base_qs.filter(diagnosis_types__id__in=diagnosis_type_ids).distinct()
        
        if bill_statuses:
            status_query = Q()
            for status in bill_statuses:
                status_query |= Q(bill_status__iexact=status)
            base_qs = base_qs.filter(status_query)
        else:
            base_qs = base_qs.filter(bill_status='Fully Paid')

        final_bills = base_qs.select_related(
            'referred_by_doctor', 'franchise_name'
        ).order_by('referred_by_doctor__first_name', 'referred_by_doctor__last_name')

        response_data = []
        for doctor, bills_iterator in groupby(final_bills, key=lambda bill: bill.referred_by_doctor):
            
            doctor_bills = list(bills_iterator)
            total_incentive = sum(bill.incentive_amount for bill in doctor_bills)
            

            serialized_doctor = IncentiveDoctorSerializer(doctor).data
            serialized_bills = IncentiveBillSerializer(doctor_bills, many=True).data

            # Keep all doctors with bills, including negative/zero totals,
            # so the frontend can surface loss-making incentive periods.
            if serialized_bills:
                response_data.append({
                    # The full doctor model is now in a nested object
                    "doctor": serialized_doctor, 
                    "total_incentive": total_incentive,
                    "bills": serialized_bills
                })
            
            # 👆 --- MODIFICATIONS END HERE --- 👆

        return Response(response_data)

class PendingReportViewSet(CenterDetailFilterMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = MinimalBillSerializerForPendingReports
    queryset = Bill.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsUserNotLocked, IsSubscriptionActive]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = BillFilter
    search_fields = [
        "bill_number",
        "patient_name",
        "bill_diagnosis_types__diagnosis_type__name",
        "bill_diagnosis_types__diagnosis_type__category__name",
        "referred_by_doctor__first_name",
        "referred_by_doctor__last_name",
    ]

    def get_queryset(self):
        base_queryset = super().get_queryset()

        return base_queryset.filter(report__isnull=True).order_by("-date_of_bill", "-id")[:40]# ========================
# CATEGORY VIEWSET
# ========================

class DiagnosisCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DiagnosisCategory with specific permissions:
    - LIST, RETRIEVE, CREATE: All authenticated users (from same center)
    - UPDATE, PARTIAL_UPDATE, DESTROY: Admin only
    """
    serializer_class = DiagnosisCategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsUserNotLocked, IsSubscriptionActive]
    
    def get_queryset(self):
        # Categories are global, not per-center
        # Order by name alphabetically
        return DiagnosisCategory.objects.filter(
            is_active=True
        ).order_by('name')
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsUserNotLocked(), IsSubscriptionActive(), IsAdminUser()]
        return [permissions.IsAuthenticated(), IsUserNotLocked(), IsSubscriptionActive()]

    def perform_create(self, serializer):
        instance = serializer.save()
        _safe_audit_log(
            user=self.request.user,
            action='CREATE',
            model_name='DiagnosisCategory',
            object_id=instance.pk,
            details=f"Created diagnosis category {instance.name}",
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        _safe_audit_log(
            user=self.request.user,
            action='UPDATE',
            model_name='DiagnosisCategory',
            object_id=instance.pk,
            details=f"Updated diagnosis category {instance.name}",
            request=self.request,
        )

    def perform_destroy(self, instance):
        category_name = instance.name
        category_id = instance.pk
        super().perform_destroy(instance)
        _safe_audit_log(
            user=self.request.user,
            action='DELETE',
            model_name='DiagnosisCategory',
            object_id=category_id,
            details=f"Deleted diagnosis category {category_name}",
            request=self.request,
        )


class CenterAuditLogListView(generics.ListAPIView):
    """
    Returns all audit logs for the authenticated admin user's center.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        IsUserNotLocked,
        IsSubscriptionActive,
        IsAdminUser,
    ]
    serializer_class = AuditLogSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        request = self.request
        user_center = getattr(request.user, 'center_detail', None)
        if user_center is None:
            raise PermissionDenied('You do not have an associated center.')

        return AuditLog.objects.filter(
            user__center_detail=user_center,
        ).select_related('user').order_by('-timestamp')
