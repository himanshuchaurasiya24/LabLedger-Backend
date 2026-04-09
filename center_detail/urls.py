from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include
router = DefaultRouter()
router.register(r'center-detail', CenterDetailViewSet)
router.register(r'subscription-plan', SubscriptionPlanViewSet)
router.register(r'active-subscription', ActiveSubscriptionViewSet)
urlpatterns = [
    path('subscription-plan-context/', SubscriptionPlanContextLookupView.as_view(), name='subscription-plan-context'),
    path('', include(router.urls)),
]