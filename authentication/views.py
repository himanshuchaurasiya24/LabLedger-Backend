# views.py

from django.conf import settings
from rest_framework.permissions import AllowAny 
from django.http import JsonResponse
from rest_framework import viewsets, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

from authentication.models import StaffAccount
from authentication.serializers import (
    StaffAccountSerializer, 
    AdminPasswordResetSerializer, 
    UserPasswordChangeSerializer
)
from center_detail.serializers import *
from diagnosis.views import CenterDetailFilterMixin, IsAdminUser

# ------------------- StaffAccount ViewSet -------------------
class StaffAccountViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = StaffAccount.objects.all()
    serializer_class = StaffAccountSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    # --- NEW METHOD TO CONTROL LIST VIEW ---
    def get_queryset(self):
        """
        Dynamically filters the queryset based on the user's role.
        - Admins get the list of users within their center.
        - Non-admins get a list containing only themselves.
        """
        user = self.request.user
        
        if user.is_admin:
            # For admins, use the default behavior from the parent classes,
            # which includes the filtering from CenterDetailFilterMixin.
            return super().get_queryset()
        else:
            # For non-admins, return a queryset containing only their own user object.
            return StaffAccount.objects.filter(pk=user.pk)
    # -----------------------------------------

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
            return Response([serializer.data])
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Allow only admins to update others. Users can update themselves."""
        user = request.user
        target_user = self.get_object()

        if not user.is_admin and user != target_user:
            return Response(
                {"error": "You do not have permission to update other user details."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        kwargs['partial'] = True
        
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {"error": f"Update failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def partial_update(self, request, *args, **kwargs):
        """Handle partial updates properly"""
        user = request.user
        target_user = self.get_object()

        if not user.is_admin and user != target_user:
            return Response(
                {"error": "You do not have permission to update other user details."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            kwargs['partial'] = True
            return super().update(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {"error": f"Update failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        target_user = self.get_object()
        requesting_user = request.user
        serializer = None
        
        if requesting_user.is_admin:
            serializer = AdminPasswordResetSerializer(data=request.data)
        
        elif requesting_user == target_user:
            serializer = UserPasswordChangeSerializer(data=request.data, context={'request': request})
        
        else:
            return Response(
                {"error": "You do not have permission to reset this password."},
                status=status.HTTP_403_FORBIDDEN
            )

        if serializer and serializer.is_valid():
            try:
                serializer.update(target_user, serializer.validated_data)
                return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {"error": f"Failed to update password: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        if serializer:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"error": "Invalid request data"},
                status=status.HTTP_400_BAD_REQUEST
            )

# ------------------- Health Check, Token, etc. (No Changes) -------------------
def health_check(request):
    return JsonResponse({'status': 'running'}, status=200)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class ValidateTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        center = getattr(user, 'center_detail', None)

        center_data = None
        if center:
            center_data = CenterDetailTokenSerializer(center).data

        return Response({
            "success": True,
            "is_admin": user.is_admin,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "id": user.id,
            "center_detail": center_data,
        })

class AppInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        min_version = getattr(settings, 'MINIMUM_APP_VERSION', None)
        
        data = {
            "minimum_required_version": min_version,
        }
        return Response(data)