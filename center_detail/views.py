from django.contrib.auth import get_user_model
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import ActiveSubscription, CenterDetail, SubscriptionPlan
from .serializers import (
    ActiveSubscriptionSerializer,
    CenterDetailListSerializer,
    CenterDetailSerializer,
    SubscriptionPlanSerializer,
)
from .permissions import (
    CenterDetailPermission,
    IsSubscriptionActive,
    SubscriptionPlanPermission,
    SubscriptionSuperUserOnly,
)

class CenterDetailViewSet(viewsets.ModelViewSet):
    queryset = CenterDetail.objects.all()
    # Add the IsSubscriptionActive permission to protect this viewset
    permission_classes = [CenterDetailPermission, IsSubscriptionActive]

    def get_queryset(self):
        base = CenterDetail.objects.select_related("active_subscription__subscription_plan")
        user = self.request.user
        if user.is_superuser:
            return base

        user_center = getattr(user, 'center_detail', None)
        if user_center is None:
            return base.none()

        return base.filter(pk=user_center.pk)

    def get_serializer_class(self):
        if self.action == "list":
            return CenterDetailListSerializer
        return CenterDetailSerializer


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """
    CRUD for dynamic subscription plans:
    - Only superusers can manage plans.
    - Plans can be reused by centers over time.
    """
    queryset = SubscriptionPlan.objects.all().order_by("name")
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [SubscriptionPlanPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            return queryset.filter(is_custom=False)
        return queryset

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [SubscriptionSuperUserOnly()]

class ActiveSubscriptionViewSet(viewsets.ModelViewSet):
    """
    CRUD for active subscriptions.
    - Only superusers can manage global assignments.
    """

    queryset = ActiveSubscription.objects.select_related("center_detail", "subscription_plan").all().order_by("center_detail__center_name")
    serializer_class = ActiveSubscriptionSerializer
    permission_classes = [SubscriptionSuperUserOnly]


class SubscriptionPlanContextLookupView(APIView):
    """
    Returns minimal plan context for login-time renewal UI.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        identifier = (request.data.get("username") or "").strip()
        User = get_user_model()

        payload = {
            "requested_identifier": identifier,
            "resolved_username": None,
            "is_admin_user": False,
            "can_show_upgrade_dialog": False,
            "center_id": None,
            "center_name": None,
            "current_plan_id": None,
            "current_plan_name": None,
            "is_expired": False,
        }

        if not identifier:
            return Response(payload)

        user = User.objects.filter(username__iexact=identifier).select_related("center_detail").first()
        if not user:
            user = User.objects.filter(email__iexact=identifier).select_related("center_detail").first()

        if not user:
            return Response(payload)

        payload["resolved_username"] = user.username
        payload["is_admin_user"] = bool(getattr(user, "is_admin", False))

        center = getattr(user, "center_detail", None)
        if not center:
            return Response(payload)

        payload["center_id"] = center.pk
        payload["center_name"] = center.center_name
        payload["can_show_upgrade_dialog"] = bool(payload["is_admin_user"])

        active_sub = getattr(center, "active_subscription", None)
        if not active_sub or not active_sub.subscription_plan_id:
            return Response(payload)

        payload["current_plan_id"] = active_sub.subscription_plan_id
        payload["current_plan_name"] = active_sub.subscription_plan.name
        payload["is_expired"] = not center.subscription_is_active
        return Response(payload)