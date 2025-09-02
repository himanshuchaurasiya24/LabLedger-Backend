from rest_framework import viewsets
from .models import CenterDetail, Subscription
from .serializers import CenterDetailListSerializer, CenterDetailSerializer, SubscriptionSerializer
from .permissions import CenterDetailPermission, SubscriptionSuperUserOnly, IsSubscriptionActive # Import the permission

class CenterDetailViewSet(viewsets.ModelViewSet):
    queryset = CenterDetail.objects.all()
    # Add the IsSubscriptionActive permission to protect this viewset
    permission_classes = [CenterDetailPermission, IsSubscriptionActive]

    def get_serializer_class(self):
        if self.action == "list":
            return CenterDetailListSerializer
        return CenterDetailSerializer

class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    CRUD for Subscriptions:
    - Only superusers can create/update/delete.
    - Center subscription is unique (one subscription per center).
    - is_active is set from API input, not auto-calculated from days left.
    """
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    # DO NOT add IsSubscriptionActive here. The existing permission is correct.
    permission_classes = [SubscriptionSuperUserOnly]

    def perform_create(self, serializer):
        # Check if a subscription already exists for this center
        center = serializer.validated_data['center']
        existing_sub = Subscription.objects.filter(center=center).first()
        if existing_sub:
            # Update existing subscription instead of creating a new one
            serializer.update(existing_sub, serializer.validated_data)
            serializer.instance = existing_sub
        else:
            # Create a new subscription
            serializer.save()

    def perform_update(self, serializer):
        # Simply save the updated fields
        serializer.save()