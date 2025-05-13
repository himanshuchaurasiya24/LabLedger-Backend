from django.shortcuts import render
from rest_framework import viewsets,permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from center_details.models import CenterDetail
from .serializers import CenterDetailSerializer


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin
    
class CenterDetailsViewset(viewsets.ModelViewSet):
    queryset = CenterDetail.objects.all()
    serializer_class= CenterDetailSerializer
    authentication_classes= [JWTAuthentication]
    permission_classes= [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':  # Restrict user creation to admins only
            return [IsAdminUser()]
        return super().get_permissions()
