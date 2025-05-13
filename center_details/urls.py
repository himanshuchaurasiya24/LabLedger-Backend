from rest_framework.routers import DefaultRouter
from .views import CenterDetailsViewset
from django.urls import path, include
router = DefaultRouter()
router.register(r'centerdetail', CenterDetailsViewset)

urlpatterns = [
    path('cd/', include(router.urls)),
]