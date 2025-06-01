from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include
router = DefaultRouter()
router.register(r'bill', BillViewset, basename='bill')
router.register(r'report', ReportViewset, basename='report')
router.register(r'doctor', DoctorViewSet, basename='doctor')
router.register(r'diagnosis-type', DiagnosisTypeViewSet, basename='diagnosis-type')

urlpatterns = [
    path('bills/', include(router.urls)),
    path('reports/', include(router.urls)),
    path('doctors/', include(router.urls)),
    path('diagnosis-types/', include(router.urls)),

]