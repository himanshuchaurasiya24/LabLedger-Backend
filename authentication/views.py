# views.py - FIXED VERSION

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
# --- UPDATED IMPORTS ---
# Import the specific serializers we just created
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

        # Use partial update to allow updating without all fields
        kwargs['partial'] = True
        
        try:
            return super().update(request, *args, **kwargs)
        except Exception as e:
            # Return detailed error information
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
        """
        Allow password update based on user role.
        - Admins can reset anyone's password (needs new 'password').
        - Regular users can update THEIR OWN password (needs 'old_password' and 'new_password').
        """
        target_user = self.get_object()
        requesting_user = request.user
        serializer = None

        # Debug print to see what data is being sent
        print(f"Reset password data received: {request.data}")
        print(f"Requesting user: {requesting_user.username}, is_admin: {requesting_user.is_admin}")
        print(f"Target user: {target_user.username}")

        if requesting_user.is_admin:
            # ADMIN FLOW: Admin is resetting this password.
            # Use the Admin serializer (only needs 'password').
            print("Using AdminPasswordResetSerializer")
            serializer = AdminPasswordResetSerializer(data=request.data)
        
        elif requesting_user == target_user:
            # USER SELF-CHANGE FLOW: User is changing their OWN password.
            # Use the User serializer (needs 'old_password', 'new_password').
            print("Using UserPasswordChangeSerializer")
            serializer = UserPasswordChangeSerializer(data=request.data, context={'request': request})
        
        else:
            # FORBIDDEN FLOW: Non-admin trying to change someone else's password.
            print("Permission denied")
            return Response(
                {"error": "You do not have permission to reset this password."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Now, validate the serializer that was chosen
        if serializer and serializer.is_valid():
            try:
                # The .update() method (defined in both serializers) handles hashing and saving.
                serializer.update(target_user, serializer.validated_data)
                print("Password updated successfully")
                return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)
            except Exception as e:
                print(f"Error during password update: {str(e)}")
                return Response(
                    {"error": f"Failed to update password: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # If serializer.is_valid() returned False or serializer is None:
        if serializer:
            print(f"Serializer errors: {serializer.errors}")
            # Return the specific error message(s) from the serializer
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                {"error": "Invalid request data"},
                status=status.HTTP_400_BAD_REQUEST
            )

# ------------------- Health Check (No Change) -------------------
def health_check(request):
    return JsonResponse({'status': 'running'}, status=200)

# ------------------- Custom JWT Token (No Change) -------------------
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# ------------------- Token Validation (No Change) -------------------
class ValidateTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        center = getattr(user, 'center_detail', None)

        center_data = None
        if center:
            # Use the token serializer to get real-time subscription info
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

# ------------------- AppInfoView (No Change) -------------------
class AppInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        min_version = getattr(settings, 'MINIMUM_APP_VERSION', None)
        
        data = {
            "minimum_required_version": min_version,
        }
        return Response(data)