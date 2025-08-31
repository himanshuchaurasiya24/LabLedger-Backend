# center_detail/views.py
from rest_framework import viewsets
from .models import CenterDetail, Subscription
from .serializers import (
    CenterDetailListSerializer,
    CenterDetailSerializer,
    SubscriptionSerializer,
)
from .permissions import CenterDetailPermission, SubscriptionSuperUserOnly


class CenterDetailViewSet(viewsets.ModelViewSet):
    queryset = CenterDetail.objects.all()
    permission_classes = [CenterDetailPermission]

    def get_serializer_class(self):
        # Use lightweight serializer for list
        if self.action == "list":
            return CenterDetailListSerializer
        # Use detailed serializer for retrieve (detail), create, update
        return CenterDetailSerializer


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [SubscriptionSuperUserOnly]
