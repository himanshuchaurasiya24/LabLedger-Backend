from rest_framework.routers import DefaultRouter
from .views import CenterDetailsViewset
from django.urls import path, include
router = DefaultRouter()
router.register(r'center-detail', CenterDetailsViewset)

urlpatterns = [
    path('center-details/', include(router.urls)),
]