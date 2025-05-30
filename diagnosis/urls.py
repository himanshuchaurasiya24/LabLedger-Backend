from rest_framework.routers import DefaultRouter
from .views import BillViewset
from django.urls import path, include
router = DefaultRouter()
router.register(r'bill', BillViewset)

urlpatterns = [
    path('bills/', include(router.urls)),
]