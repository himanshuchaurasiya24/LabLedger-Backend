from rest_framework import viewsets, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from authentication.models import StaffAccount
from authentication.serializers import StaffAccountSerializer

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin

class StaffAccountViewSet(viewsets.ModelViewSet):
    queryset = StaffAccount.objects.all()
    serializer_class = StaffAccountSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]  # Default permission

    def get_permissions(self):
        if self.action == 'create':  # Restrict user creation to admins only
            return [IsAdminUser()]
        return super().get_permissions()