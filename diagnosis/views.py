from rest_framework import viewsets,permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import *
from .serializers import *



class CenterDetailFilterMixin:
    def get_queryset(self):
        model = self.queryset.model
        if self.request.user.center_detail is None:
            return model.objects.none()
        return model.objects.filter(center_detail=self.request_detail)

    @property
    def request_detail(self):
        return self.request.user.center_detail
    

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin


class DoctorViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset= Doctor.objects.all()
    serializer_class = DoctorSerializer
    authentication_classes= [JWTAuthentication ]
    permission_classes = [IsAdminUser,permissions.IsAuthenticated]
class DiagnosisTypeViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = DiagnosisType.objects.all()
    serializer_class = DiagnosisTypeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser, permissions.IsAuthenticated]



class BillViewset(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

class ReportViewset(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
