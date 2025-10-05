from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include
router = DefaultRouter()
router.register(r'center-detail', CenterDetailViewSet)
router.register(r'subscription', SubscriptionViewSet)
urlpatterns = [
    path('', include(router.urls)),
]