from rest_framework import viewsets,permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import *
from .serializers import *
import django_filters
from .filters import *




class CenterDetailFilterMixin:
    def get_queryset(self):
        model = self.queryset.model
        if self.request.user.center_detail is None:
            return model.objects.none()
        return model.objects.filter(center_detail=self.request.user.center_detail)

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
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = DoctorFilter
    search_fields = ['first_name', 'last_name', 'phone_number']
class DiagnosisTypeViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = DiagnosisType.objects.all()
    serializer_class = DiagnosisTypeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser, permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = DiagnosisTypeFilter
    search_fields = ['name', 'description']



class BillViewset(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = BillFilter
    search_fields = ['bill_number', 'patient_name']

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(test_done_by=user, center_detail=user.center_detail)

    def perform_update(self, serializer):
        user = self.request.user
        serializer.save(test_done_by=user, center_detail=user.center_detail)

class PatientReportViewset(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = PatientReport.objects.all()
    serializer_class = PatientReportSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = PatientReportFilter
    search_fields = ['patient_name', 'report_title']
