from rest_framework.routers import DefaultRouter
from authentication.views import StaffAccountViewSet
from django.urls import path, include
router = DefaultRouter()
router.register(r'auth', StaffAccountViewSet)

urlpatterns = [
    path('auth/', include(router.urls)),
]