from django.shortcuts import render
from rest_framework import viewsets,permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from center_detail.filters import CenterDetailFilter
from .models import CenterDetail
from .serializers import CenterDetailSerializer


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin
    
class CenterDetailsViewset(viewsets.ModelViewSet):
    queryset = CenterDetail.objects.all()
    serializer_class= CenterDetailSerializer
    authentication_classes= [JWTAuthentication]
    permission_classes= [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = CenterDetailFilter
    search_fields = ['center_name', 'address', 'owner_phone', 'owner_name']
    def get_permissions(self):
        if self.action == 'create':  # Restrict user creation to admins only
            return [IsAdminUser()]
        return super().get_permissions()
