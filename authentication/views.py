from django.conf import settings
from django.http import JsonResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView

from authentication.models import StaffAccount
from authentication.serializers import (
    AdminPasswordResetSerializer,
    CustomTokenObtainPairSerializer,
    StaffAccountSerializer,
    UserPasswordChangeSerializer
)
from center_detail.serializers import *
from diagnosis.views import CenterDetailFilterMixin, IsAdminUser
from diagnosis.models import AuditLog


def _safe_audit_log(user, action, model_name, object_id='', details='', request=None):
    """
    Best-effort audit logger so auth operations keep working on log failure.
    """
    try:
        ip_address = None
        user_agent = ''
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=str(object_id) if object_id else None,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception:
        pass

class StaffAccountViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = StaffAccount.objects.all()
    serializer_class = StaffAccountSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        if user.is_admin:
            return super().get_queryset()
        else:
            return StaffAccount.objects.filter(pk=user.pk)

    def get_permissions(self):
        if self.action == 'create':
            return [IsAdminUser()]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        user = request.user
        target_user = self.get_object()
        if not user.is_admin and user != target_user:
            return Response({"error": "You do not have permission to update other user details."}, status=status.HTTP_403_FORBIDDEN)
        
        kwargs['partial'] = True
        try:
            return super().update(request, *args, **kwargs)
        except Exception:
            return Response({"error": "Update failed."}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        user = request.user
        target_user = self.get_object()
        if not user.is_admin and user != target_user:
            return Response({"error": "You do not have permission to update other user details."}, status=status.HTTP_403_FORBIDDEN)

        try:
            kwargs['partial'] = True
            return super().update(request, *args, **kwargs)
        except Exception:
            return Response({"error": "Update failed."}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        instance = serializer.save()
        _safe_audit_log(
            user=self.request.user,
            action='CREATE',
            model_name='StaffAccount',
            object_id=instance.pk,
            details=f"Created staff user {instance.username}",
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        previous_is_admin = instance.is_admin
        previous_is_locked = instance.is_locked

        updated_instance = serializer.save()

        _safe_audit_log(
            user=self.request.user,
            action='UPDATE',
            model_name='StaffAccount',
            object_id=updated_instance.pk,
            details=f"Updated staff user {updated_instance.username}",
            request=self.request,
        )

        if (
            previous_is_admin != updated_instance.is_admin
            or previous_is_locked != updated_instance.is_locked
        ):
            _safe_audit_log(
                user=self.request.user,
                action='PRIVILEGE_CHANGE',
                model_name='StaffAccount',
                object_id=updated_instance.pk,
                details=(
                    f"Privilege change for {updated_instance.username}: "
                    f"is_admin {previous_is_admin}->{updated_instance.is_admin}, "
                    f"is_locked {previous_is_locked}->{updated_instance.is_locked}"
                ),
                request=self.request,
            )

    def perform_destroy(self, instance):
        username = instance.username
        user_id = instance.pk
        super().perform_destroy(instance)
        _safe_audit_log(
            user=self.request.user,
            action='DELETE',
            model_name='StaffAccount',
            object_id=user_id,
            details=f"Deleted staff user {username}",
            request=self.request,
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
            return Response({"error": "You do not have permission to reset this password."}, status=status.HTTP_403_FORBIDDEN)

        if serializer and serializer.is_valid():
            try:
                serializer.update(target_user, serializer.validated_data)
                action = 'PASSWORD_CHANGE'
                details = f"Password updated for user {target_user.username}"
                _safe_audit_log(
                    user=requesting_user,
                    action=action,
                    model_name='StaffAccount',
                    object_id=target_user.pk,
                    details=details,
                    request=request,
                )
                return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)
            except Exception:
                return Response({"error": "Failed to update password."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if serializer:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Invalid request data"}, status=status.HTTP_400_BAD_REQUEST)

def health_check(request):
    return JsonResponse({'status': 'running'}, status=200)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            user_id = response.data.get('id')
            user = StaffAccount.objects.filter(pk=user_id).first() if user_id else None
            _safe_audit_log(
                user=user,
                action='LOGIN',
                model_name='StaffAccount',
                object_id=user_id,
                details=f"User login successful for {user.username}" if user else "User login successful",
                request=request,
            )
        return response


class LogoutView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _safe_audit_log(
            user=request.user,
            action='LOGOUT',
            model_name='StaffAccount',
            object_id=request.user.pk,
            details=f"User logout for {request.user.username}",
            request=request,
        )
        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

class ValidateTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Check if the user is locked and return 403 Forbidden
        if user.is_locked:
            return Response(
                {"detail": "User account is locked."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        if not user.is_superuser:
            center = getattr(user, 'center_detail', None)
            if center and not center.subscription_is_active:
                return Response(
                    {"detail": "Your subscription is inactive or has expired. Please renew to continue."},
                    status=status.HTTP_403_FORBIDDEN,
                )

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
            "is_locked": user.is_locked,
            "center_detail": center_data,
        })

class AppInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        min_version = getattr(settings, 'MINIMUM_APP_VERSION', None)
        data = {"minimum_required_version": min_version}
        return Response(data)