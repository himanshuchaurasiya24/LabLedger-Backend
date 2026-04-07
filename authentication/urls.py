from rest_framework.routers import DefaultRouter
from authentication.views import StaffAccountViewSet, LogoutView
from django.urls import path, include
router = DefaultRouter()
router.register(r'staff', StaffAccountViewSet)

urlpatterns = [
    path('staffs/', include(router.urls)),
    path('logout/', LogoutView.as_view(), name='logout'),
    
]
# http://127.0.0.1:8000/auth/staff/staff/1/reset_password/ to reset password
