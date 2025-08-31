from django.http import JsonResponse
from rest_framework import viewsets, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import StaffAccount
from authentication.serializers import StaffAccountSerializer, PasswordResetSerializer
from center_detail.serializers import *
from diagnosis.views import CenterDetailFilterMixin, IsAdminUser


# ------------------- StaffAccount ViewSet -------------------
class StaffAccountViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = StaffAccount.objects.all()
    serializer_class = StaffAccountSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]  # Default

    def get_permissions(self):
        """Restrict user creation to admins only"""
        if self.action == 'create':
            return [IsAdminUser()]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        """Retrieve single staff with optional list format"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])  # List-wrapped
        return Response(serializer.data)  # Normal

    def update(self, request, *args, **kwargs):
        """Allow only admins to update others. Users can update themselves."""
        user = request.user
        target_user = self.get_object()

        if not user.is_admin and user != target_user:
            return Response(
                {"error": "You do not have permission to update other user details."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Allow password reset for self or by admin."""
        user = self.get_object()
        requesting_user = request.user

        if not requesting_user.is_admin and requesting_user != user:
            return Response(
                {"error": "You can only reset your own password."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.update(user, serializer.validated_data)
            return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ------------------- Health Check -------------------
def health_check(request):
    return JsonResponse({'status': 'running'}, status=200)


# ------------------- Custom JWT Token -------------------
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ------------------- Token Validation -------------------
# authentication.py
class ValidateTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return basic user + center detail info (including subscription)."""
        user = request.user
        center = getattr(user, 'center_detail', None)

        center_data = None
        if center:
            center_data = CenterDetailTokenSerializer(center).data

        return Response({
            "is_admin": user.is_admin,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "id": user.id,
            "center_detail": center_data,
        })

