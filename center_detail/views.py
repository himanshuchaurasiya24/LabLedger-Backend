from rest_framework import viewsets,permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
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
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])  # List-wrapped
        return Response(serializer.data)  # Normal
