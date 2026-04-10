from rest_framework.routers import DefaultRouter
from authentication.views import StaffAccountViewSet, LogoutView
from django.urls import path, include
from all_urls import AUTH_LOGOUT, AUTH_STAFF_ROUTER, AUTH_STAFFS

router = DefaultRouter()
router.register(AUTH_STAFF_ROUTER, StaffAccountViewSet)

urlpatterns = [
    path(AUTH_STAFFS, include(router.urls)),
    path(AUTH_LOGOUT, LogoutView.as_view(), name='logout'),
    
]
# Example reset password endpoint:
# http://127.0.0.1:8000/auth/staffs/staff/1/reset_password/
