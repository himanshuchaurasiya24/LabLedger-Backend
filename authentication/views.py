from django.http import JsonResponse
from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from authentication.models import StaffAccount
from authentication.serializers import StaffAccountSerializer,PasswordResetSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from diagnosis.views import CenterDetailFilterMixin
class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin

class StaffAccountViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = StaffAccount.objects.all()
    serializer_class = StaffAccountSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]  # Default permission

    def get_permissions(self):
        if self.action == 'create':  # Restrict user creation to admins only
            return [IsAdminUser()]
        return super().get_permissions()
    def update(self, request, *args, **kwargs):
        # Allow only admins to update user details
        if not request.user.is_admin and request.user != self.get_object():
            return Response(
                {"error": "You do not have permission to update other user details."},
                status=status.HTTP_403_FORBIDDEN
            )
    
        if request.user != self.get_object() and not request.user.is_admin:
            return Response(
                {"error": "You can only update your own details."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
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
    

def health_check(request):
    return JsonResponse({'status': 'running', }, status=200)

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class ValidateTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "success": True,
            "is_admin": user.is_admin , # ✅ custom field
            "username":user.username,
            "first_name":user.first_name,
            "last_name":user.last_name,
            "id":user.id,
        })

