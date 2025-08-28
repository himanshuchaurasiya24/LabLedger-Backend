from datetime import datetime, timedelta
from django.db.models.functions import Concat
from django.utils.timezone import now, make_aware
from django.db.models import Count, Q, Sum, Value
from rest_framework import viewsets,permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import *
from .serializers import *
from rest_framework.response import Response
from .filters import *
from rest_framework.decorators import action
from django.db.models import Count
from rest_framework.views import APIView
from datetime import date
from calendar import monthrange

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
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsAdminUser]
        else:  # list, retrieve
            permission_classes = [permissions.IsAuthenticated]
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
            return Response([serializer.data])  # List-wrapped
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
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsAdminUser]
        else:  # list, retrieve
            permission_classes = [permissions.IsAuthenticated]
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
            return Response([serializer.data])  # List-wrapped
        return Response(serializer.data)  # Normal

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
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsAdminUser]
        else:  # list, retrieve
            permission_classes = [permissions.IsAuthenticated]
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
    """
    Returns top referrals (referred_by_doctor) with full name,
    breakdowns (ultrasound, ecg, xray, pathology, franchise_lab),
    and total incentive amount for this week, month, year, and all time.
    Can filter by ?referred_by_doctor=<id>
    """

    def list(self, request):
        today = now().date()

        # Create timezone-aware datetimes
        start_of_week = make_aware(datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time()))
        start_of_month = make_aware(datetime.combine(today.replace(day=1), datetime.min.time()))
        start_of_year = make_aware(datetime.combine(today.replace(month=1, day=1), datetime.min.time()))

        # Read query param
        doctor_id = request.query_params.get("referred_by_doctor")

        def get_referral_stats(qs):
            if doctor_id:
                qs = qs.filter(referred_by_doctor_id=doctor_id)

            return (
                qs.annotate(
                    doctor_full_name=Concat(
                        "referred_by_doctor__first_name",
                        Value(" "),
                        "referred_by_doctor__last_name",
                    )
                )
                .values("referred_by_doctor__id", "doctor_full_name")
                .annotate(
                    total=Count("id"),
                    ultrasound=Count("id", filter=Q(diagnosis_type__category="Ultrasound")),
                    ecg=Count("id", filter=Q(diagnosis_type__category="ECG")),
                    xray=Count("id", filter=Q(diagnosis_type__category="X-Ray")),
                    pathology=Count("id", filter=Q(diagnosis_type__category="Pathology")),
                    franchise_lab=Count("id", filter=Q(diagnosis_type__category="Franchise Lab")),
                    incentive_amount=Sum("incentive_amount"),
                )
                .order_by("-total")
            )

        data = {
            "this_week": list(get_referral_stats(Bill.objects.filter(date_of_bill__gte=start_of_week))),
            "this_month": list(get_referral_stats(Bill.objects.filter(date_of_bill__gte=start_of_month))),
            "this_year": list(get_referral_stats(Bill.objects.filter(date_of_bill__gte=start_of_year))),
            "all_time": list(get_referral_stats(Bill.objects.all())),
        }

        return Response(data)
from django.db.models.functions import TruncDate
class BillChartStatsViewSet(viewsets.ViewSet):
    """
    Returns chart data of bills grouped by date_of_bill
    with total count and category breakdowns
    for this week, this month, this year, and all time.
    """

    def list(self, request):
        today = now().date()

        # Create timezone-aware datetimes (fix: include time arg!)
        start_of_week = make_aware(datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time()))
        start_of_month = make_aware(datetime.combine(today.replace(day=1), datetime.min.time()))
        start_of_year = make_aware(datetime.combine(today.replace(month=1, day=1), datetime.min.time()))
        # Read query param
        doctor_id = request.query_params.get("referred_by_doctor")
        def get_chart_stats(qs):
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

        data = {
            "this_week": list(get_chart_stats(Bill.objects.filter(date_of_bill__gte=start_of_week))),
            "this_month": list(get_chart_stats(Bill.objects.filter(date_of_bill__gte=start_of_month))),
            "this_year": list(get_chart_stats(Bill.objects.filter(date_of_bill__gte=start_of_year))),
            "all_time": list(get_chart_stats(Bill.objects.all())),
        }

        return Response(data)

class BillGrowthStatsView(APIView):
    """
    Returns aggregated stats based on `date_of_bill`:
    - Current month vs previous month
    - Current year vs previous year
    - Current quarter vs previous quarter
    """

    def get_quarter_range(self, year, quarter):
        """Return first and last date of a given quarter"""
        if quarter == 1:
            return date(year, 1, 1), date(year, 3, 31)
        elif quarter == 2:
            return date(year, 4, 1), date(year, 6, 30)
        elif quarter == 3:
            return date(year, 7, 1), date(year, 9, 30)
        else:  # quarter 4
            return date(year, 10, 1), date(year, 12, 31)

    def get(self, request, format=None):
        today = date.today()

        # Helper: first and last day of a month
        def month_range(year, month):
            first_day = date(year, month, 1)
            last_day = date(year, month, monthrange(year, month)[1])
            return first_day, last_day

        # ---------- Current Month ----------
        first_day_curr_month, last_day_curr_month = month_range(today.year, today.month)
        current_month_qs = BillFilter(
            data={'bill_start_date': first_day_curr_month, 'bill_end_date': last_day_curr_month},
            queryset=Bill.objects.all()
        ).qs

        # ---------- Previous Month ----------
        if today.month == 1:
            prev_month = 12
            prev_month_year = today.year - 1
        else:
            prev_month = today.month - 1
            prev_month_year = today.year

        first_day_prev_month, last_day_prev_month = month_range(prev_month_year, prev_month)
        previous_month_qs = BillFilter(
            data={'bill_start_date': first_day_prev_month, 'bill_end_date': last_day_prev_month},
            queryset=Bill.objects.all()
        ).qs

        # ---------- Current Year ----------
        first_day_curr_year = date(today.year, 1, 1)
        last_day_curr_year = date(today.year, 12, 31)
        current_year_qs = BillFilter(
            data={'bill_start_date': first_day_curr_year, 'bill_end_date': last_day_curr_year},
            queryset=Bill.objects.all()
        ).qs

        # ---------- Previous Year ----------
        last_year = today.year - 1
        first_day_prev_year = date(last_year, 1, 1)
        last_day_prev_year = date(last_year, 12, 31)
        previous_year_qs = BillFilter(
            data={'bill_start_date': first_day_prev_year, 'bill_end_date': last_day_prev_year},
            queryset=Bill.objects.all()
        ).qs

        # ---------- Current Quarter ----------
        current_quarter = (today.month - 1) // 3 + 1
        first_day_curr_quarter, last_day_curr_quarter = self.get_quarter_range(today.year, current_quarter)
        current_quarter_qs = BillFilter(
            data={'bill_start_date': first_day_curr_quarter, 'bill_end_date': last_day_curr_quarter},
            queryset=Bill.objects.all()
        ).qs

        # ---------- Previous Quarter ----------
        if current_quarter == 1:
            prev_quarter = 4
            prev_quarter_year = today.year - 1
        else:
            prev_quarter = current_quarter - 1
            prev_quarter_year = today.year

        first_day_prev_quarter, last_day_prev_quarter = self.get_quarter_range(prev_quarter_year, prev_quarter)
        previous_quarter_qs = BillFilter(
            data={'bill_start_date': first_day_prev_quarter, 'bill_end_date': last_day_prev_quarter},
            queryset=Bill.objects.all()
        ).qs

        # ---------- Aggregation ----------
        # Example inside your aggregate function
        def aggregate(qs):
            total_bills = qs.count()
            diagnosis_counts = (
                qs.values('diagnosis_type__category')
                .annotate(count=Count('id'))
            )
            counts_dict = {item['diagnosis_type__category']: item['count'] for item in diagnosis_counts}
            return {
                "total_bills": total_bills,
                "diagnosis_counts": counts_dict
            }

        data = {
            "current_month": aggregate(current_month_qs),
            "previous_month": aggregate(previous_month_qs),
            "current_year": aggregate(current_year_qs),
            "previous_year": aggregate(previous_year_qs),
            "current_quarter": aggregate(current_quarter_qs),
            "previous_quarter": aggregate(previous_quarter_qs),
        }

        return Response(data)


class BillViewset(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = BillFilter

    # Recommended search fields
    search_fields = [
        "bill_number",
        "patient_name",
        "diagnosis_type__name",
        "referred_by_doctor__first_name",
        "referred_by_doctor__last_name",
        "franchise_name",
        "bill_status",
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        query = request.query_params.get("search", "").strip().lower()

        results = []
        for bill in queryset:
            match_reason = []

            if query:
                if bill.bill_number and query in bill.bill_number.lower():
                    match_reason.append("Matching Bill")
                if bill.patient_name and query in bill.patient_name.lower():
                    match_reason.append("Matching Patient")
                if bill.franchise_name and query in bill.franchise_name.lower():
                    match_reason.append("Matching Franchise")
                if bill.referred_by_doctor:
                    if bill.referred_by_doctor.first_name and query in bill.referred_by_doctor.first_name.lower():
                        match_reason.append("Matching Doctor")
                    if bill.referred_by_doctor.last_name and query in bill.referred_by_doctor.last_name.lower():
                        match_reason.append("Matching Doctor")
                if bill.diagnosis_type and query in bill.diagnosis_type.name.lower():
                    match_reason.append("Matching Diagnosis Type")
                if bill.bill_status and query in bill.bill_status.lower():
                    match_reason.append("Matching Bill Status")

            serializer = self.get_serializer(bill, context={"request": request})
            bill_data = serializer.data
            bill_data["match_reason"] = match_reason
            results.append(bill_data)

        return Response(results)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by("-id")

    @action(detail=False, methods=["get"], url_path="franchise-names")
    def franchise_names(self, request):
        franchises = (
            Bill.objects.exclude(franchise_name__isnull=True)
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
            return Response([serializer.data])  # List-wrapped
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
    permission_classes = [permissions.IsAuthenticated]
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
            return Response([serializer.data])  # List-wrapped
        return Response(serializer.data)  # Normal

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)

class SampleTestReportViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = SampleTestReport.objects.all()
    serializer_class = SampleTestReportSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
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
            return Response([serializer.data])  # List-wrapped
        return Response(serializer.data)  # Normal

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)
