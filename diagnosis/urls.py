from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include
from all_urls import (
    DIAG_AUDIT_LOGS,
    DIAG_BILL_CHART_STAT_ROUTER,
    DIAG_BILL_ROUTER,
    DIAG_BILLS_GROWTH_STATS,
    DIAG_CATEGORIES_ROUTER,
    DIAG_DIAGNOSIS_TYPE_ROUTER,
    DIAG_DOCTOR_GROWTH_STATS,
    DIAG_DOCTOR_INCENTIVES,
    DIAG_DOCTOR_ROUTER,
    DIAG_FRANCHISE_NAME_ROUTER,
    DIAG_INCENTIVES,
    DIAG_PATIENT_REPORT_ROUTER,
    DIAG_PENDING_REPORTS_ROUTER,
    DIAG_REFERRAL_STAT_ROUTER,
    DIAG_SAMPLE_TEST_REPORT_ROUTER,
)

# 1. Register all your ViewSets with the router
router = DefaultRouter()
router.register(DIAG_BILL_ROUTER, BillViewset, basename='bill')
router.register(DIAG_PATIENT_REPORT_ROUTER, PatientReportViewset, basename='patient-report')
router.register(DIAG_DOCTOR_ROUTER, DoctorViewSet, basename='doctor')
router.register(DIAG_DIAGNOSIS_TYPE_ROUTER, DiagnosisTypeViewSet, basename='diagnosis-type')
router.register(DIAG_SAMPLE_TEST_REPORT_ROUTER, SampleTestReportViewSet, basename='sample-test-report')
router.register(DIAG_FRANCHISE_NAME_ROUTER, FranchiseNameViewSet, basename='franchise-name')
router.register(DIAG_REFERRAL_STAT_ROUTER, ReferralStatsViewSet, basename='referral-stats')
router.register(DIAG_BILL_CHART_STAT_ROUTER, BillChartStatsViewSet, basename='bill-chart-stats')
router.register(DIAG_PENDING_REPORTS_ROUTER, PendingReportViewSet, basename='pending-report')
router.register(DIAG_CATEGORIES_ROUTER, DiagnosisCategoryViewSet, basename='category')


urlpatterns = [
    path('', include(router.urls)), 
    path(DIAG_AUDIT_LOGS, CenterAuditLogListView.as_view(), name='center-audit-logs'),
    path(DIAG_DOCTOR_INCENTIVES, DoctorIncentiveStatsView.as_view(), name='doctor-incentive-stats'),
    path(DIAG_DOCTOR_GROWTH_STATS, DoctorBillGrowthStatsView.as_view(), name='doctor-growth-stats'),
    path(DIAG_BILLS_GROWTH_STATS, BillGrowthStatsView.as_view(), name='bill-growth-stats'),
    path(DIAG_INCENTIVES, FlexibleIncentiveReportView.as_view(), name='flexible-incentive-report'),
]