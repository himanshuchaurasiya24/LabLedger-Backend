from rest_framework.routers import DefaultRouter
from .views import *
from django.urls import path, include
from all_urls import (
    CENTER_ACTIVE_SUBSCRIPTION_ROUTER,
    CENTER_DETAIL_ROUTER,
    CENTER_SUBSCRIPTION_PLAN_CONTEXT,
    CENTER_SUBSCRIPTION_PLAN_ROUTER,
)

router = DefaultRouter()
router.register(CENTER_DETAIL_ROUTER, CenterDetailViewSet)
router.register(CENTER_SUBSCRIPTION_PLAN_ROUTER, SubscriptionPlanViewSet)
router.register(CENTER_ACTIVE_SUBSCRIPTION_ROUTER, ActiveSubscriptionViewSet)
urlpatterns = [
    path(CENTER_SUBSCRIPTION_PLAN_CONTEXT, SubscriptionPlanContextLookupView.as_view(), name='subscription-plan-context'),
    path('', include(router.urls)),
]