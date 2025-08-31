from rest_framework import viewsets
from .models import CenterDetail, Subscription
from .serializers import CenterDetailListSerializer, CenterDetailSerializer, SubscriptionSerializer
from .permissions import CenterDetailPermission, SubscriptionSuperUserOnly


class CenterDetailViewSet(viewsets.ModelViewSet):
    queryset = CenterDetail.objects.all()
    permission_classes = [CenterDetailPermission]

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
    permission_classes = [SubscriptionSuperUserOnly]

    def perform_create(self, serializer):
        # Check if a subscription already exists for this center
        center = serializer.validated_data['center']
        existing_sub = Subscription.objects.filter(center=center).first()
        if existing_sub:
            # Update existing subscription instead of creating a new one
            for attr, value in serializer.validated_data.items():
                setattr(existing_sub, attr, value)
            existing_sub.save()
            serializer.instance = existing_sub
        else:
            # Create a new subscription
            serializer.save()

    def perform_update(self, serializer):
        # Simply save the updated fields
        serializer.save()
# class SubscriptionViewSet(viewsets.ModelViewSet):
#     queryset = Subscription.objects.all()
#     serializer_class = SubscriptionSerializer
#     permission_classes = [SubscriptionSuperUserOnly]

#     def perform_create(self, serializer):
#         sub = serializer.save()
#         # sub.is_active = sub.days_left > 0
#         sub.save()

#     def perform_update(self, serializer):
#         sub = serializer.save()
#         # sub.is_active = sub.days_left > 0
#         sub.save()
