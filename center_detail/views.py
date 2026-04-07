from rest_framework import viewsets
from .models import CenterDetail, SubscriptionPlan
from .serializers import (
    CenterDetailListSerializer,
    CenterDetailSerializer,
    SubscriptionPlanSerializer,
)
from .permissions import CenterDetailPermission, SubscriptionSuperUserOnly, IsSubscriptionActive # Import the permission

class CenterDetailViewSet(viewsets.ModelViewSet):
    queryset = CenterDetail.objects.all()
    # Add the IsSubscriptionActive permission to protect this viewset
    permission_classes = [CenterDetailPermission, IsSubscriptionActive]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return CenterDetail.objects.all()

        user_center = getattr(user, 'center_detail', None)
        if user_center is None:
            return CenterDetail.objects.none()

        return CenterDetail.objects.filter(pk=user_center.pk)

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
    permission_classes = [SubscriptionSuperUserOnly]