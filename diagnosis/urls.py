from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include

# 1. Register all your ViewSets with the router
router = DefaultRouter()
router.register(r'bill', BillViewset, basename='bill')
router.register(r'patient-report', PatientReportViewset, basename='patient-report')
router.register(r'doctor', DoctorViewSet, basename='doctor')
router.register(r'diagnosis-type', DiagnosisTypeViewSet, basename='diagnosis-type')
router.register(r'sample-test-report', SampleTestReportViewSet, basename='sample-test-report')
router.register(r'franchise-name', FranchiseNameViewSet, basename='franchise-name')
router.register(r'referral-stat', ReferralStatsViewSet, basename='referral-stats')
router.register(r'bill-chart-stat', BillChartStatsViewSet, basename='bill-chart-stats')
router.register(r'pending-reports', PendingReportViewSet, basename='pending-report')


urlpatterns = [
    path('', include(router.urls)), 
    path('doctors/<int:doctor_id>/incentives/', DoctorIncentiveStatsView.as_view(), name='doctor-incentive-stats'),
    path('doctors/<int:doctor_id>/growth-stats/', DoctorBillGrowthStatsView.as_view(), name='doctor-growth-stats'),
    path('bills/growth-stats/', BillGrowthStatsView.as_view(), name='bill-growth-stats'),
    path('incentives/', FlexibleIncentiveReportView.as_view(), name='flexible-incentive-report'),
]