from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include
router = DefaultRouter()
router.register(r'bill', BillViewset)
router.register(r'report', ReportViewset, basename='report')

urlpatterns = [
    path('bills/', include(router.urls)),
    path('reports/', include(router.urls)),
]