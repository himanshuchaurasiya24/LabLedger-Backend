from rest_framework.routers import DefaultRouter
from authentication.views import StaffAccountViewSet
from django.urls import path, include
router = DefaultRouter()
router.register(r'staff', StaffAccountViewSet)

urlpatterns = [
    path('staff/', include(router.urls)),
]