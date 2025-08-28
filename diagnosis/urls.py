from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include
router = DefaultRouter()
router.register(r'bill', BillViewset, basename='bill')
router.register(r'patient-report', PatientReportViewset, basename='patient-report')
router.register(r'doctor', DoctorViewSet, basename='doctor')
router.register(r'diagnosis-type', DiagnosisTypeViewSet, basename='diagnosis-type')
router.register(r'sample-test-report', SampleTestReportViewSet, basename='sample-test-report')
router.register(r'franchise-name', FranchiseNameViewSet, basename='franchise-name')
router.register(r'referral-stat', ReferralStatsViewSet, basename='referral-stats')
router.register(r'bill-chart-stat', BillChartStatsViewSet, basename='bill-chart-stats')

urlpatterns = [
    path('bills/', include(router.urls)),
    path('patient-reports/', include(router.urls)),
    path('doctors/', include(router.urls)),
    path('diagnosis-types/', include(router.urls)),
    path('sample-test-reports/', include(router.urls)),
    path('referral-stats/', include(router.urls)),
    path('bill-chart-stats/', include(router.urls)),
    path('franchise-names/', include(router.urls)),
     path('bills/growth-stats/', BillGrowthStatsView.as_view(), name='bill-growth-stats'),
]