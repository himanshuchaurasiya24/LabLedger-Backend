from rest_framework import viewsets,permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import *
from .serializers import *
from rest_framework.response import Response
from .filters import *
from rest_framework.decorators import action


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


# class DoctorViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
#     queryset= Doctor.objects.all()
#     serializer_class = DoctorSerializer
#     authentication_classes= [JWTAuthentication ]
#     permission_classes = [IsAdminUser,permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, SearchFilter]
#     filterset_class = DoctorFilter
#     search_fields = ['first_name', 'last_name', 'phone_number']
#     def perform_create(self, serializer):
#         user = self.request.user
#         if not user.center_detail:
#             raise ValidationError("User does not have an associated center.")
#         serializer.save(center_detail=user.center_detail)

#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         serializer = self.get_serializer(instance)
        
#         if request.query_params.get("list_format") == "true":
#             return Response([serializer.data])  # List-wrapped
#         return Response(serializer.data)
#     def perform_update(self, serializer):
#         user = self.request.user
#         if not user.center_detail:
#             raise ValidationError("User does not have an associated center.")
#         serializer.save(center_detail=user.center_detail)

class DoctorViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = DoctorFilter
    search_fields = ['first_name', 'last_name', 'phone_number']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsAdminUser]
        else:  # list, retrieve
            permission_classes = [permissions.IsAuthenticated]
        return [perm() for perm in permission_classes]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])  # List-wrapped
        return Response(serializer.data)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)

# class DiagnosisTypeViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
#     queryset = DiagnosisType.objects.all()
#     serializer_class = DiagnosisTypeSerializer
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAdminUser, permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, SearchFilter]
#     filterset_class = DiagnosisTypeFilter
#     search_fields = ['name', 'description']
#     def perform_create(self, serializer):
#         user = self.request.user
#         if not user.center_detail:
#             raise ValidationError("User does not have an associated center.")
#         serializer.save(center_detail=user.center_detail)
#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         serializer = self.get_serializer(instance)
        
#         if request.query_params.get("list_format") == "true":
#             return Response([serializer.data])  # List-wrapped
#         return Response(serializer.data)  # Normal

#     def perform_update(self, serializer):
#         user = self.request.user
#         if not user.center_detail:
#             raise ValidationError("User does not have an associated center.")
#         serializer.save(center_detail=user.center_detail)



# class FranchiseNameViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
#     serializer_class = FranchiseNameSerializer
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAdminUser,permissions.IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, SearchFilter]
#     search_fields = ['franchise_name', 'address', 'phone_number']

#     def get_queryset(self):
#         user_center = self.request.user.center_detail
#         return FranchiseName.objects.filter(center_detail=user_center)

#     def perform_create(self, serializer):
#         user = self.request.user
#         if not user.center_detail:
#             raise ValidationError("User does not have an associated center.")
#         serializer.save(center_detail=user.center_detail)

#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         if instance.center_detail != request.user.center_detail:
#             return Response({'detail': 'You do not have permission to access this franchise.'}, status=403)
#         serializer = self.get_serializer(instance)
#         return Response(serializer.data)

#     def perform_update(self, serializer):
#         instance = self.get_object()
#         user = self.request.user  # <-- define user here
#         if instance.center_detail != user.center_detail:
#             raise ValidationError("You cannot update franchise from another center.")
#         serializer.save(center_detail=user.center_detail)

class DiagnosisTypeViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = DiagnosisType.objects.all()
    serializer_class = DiagnosisTypeSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = DiagnosisTypeFilter
    search_fields = ['name', 'description']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsAdminUser]
        else:  # list, retrieve
            permission_classes = [permissions.IsAuthenticated]
        return [perm() for perm in permission_classes]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])  # List-wrapped
        return Response(serializer.data)  # Normal

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)


class FranchiseNameViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    serializer_class = FranchiseNameSerializer
    authentication_classes = [JWTAuthentication]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['franchise_name', 'address', 'phone_number']

    def get_queryset(self):
        user_center = self.request.user.center_detail
        return FranchiseName.objects.filter(center_detail=user_center)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsAdminUser]
        else:  # list, retrieve
            permission_classes = [permissions.IsAuthenticated]
        return [perm() for perm in permission_classes]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.center_detail != request.user.center_detail:
            return Response(
                {'detail': 'You do not have permission to access this franchise.'},
                status=403
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_update(self, serializer):
        instance = self.get_object()
        user = self.request.user
        if instance.center_detail != user.center_detail:
            raise ValidationError("You cannot update franchise from another center.")
        serializer.save(center_detail=user.center_detail)



class BillViewset(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = BillFilter
    search_fields = ['bill_number', 'patient_name']
    @action(detail=False, methods=['get'], url_path='franchise-names')
    def franchise_names(self, request):
        franchises = Bill.objects.exclude(franchise_name__isnull=True).exclude(franchise_name__exact='').values_list('franchise_name', flat=True).distinct()
        return Response(franchises)
    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(test_done_by=user, center_detail=user.center_detail)
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])  # List-wrapped
        return Response(serializer.data)  # Normal

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(test_done_by=user, center_detail=user.center_detail)

class PatientReportViewset(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = PatientReport.objects.all()
    serializer_class = PatientReportSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = PatientReportFilter
    search_fields = ['patient_name', 'report_title']
    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])  # List-wrapped
        return Response(serializer.data)  # Normal

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)

class SampleTestReportViewSet(CenterDetailFilterMixin, viewsets.ModelViewSet):
    queryset = SampleTestReport.objects.all()
    serializer_class = SampleTestReportSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = SampleTestReportFilter
    search_fields = ["diagnosis_type", "diagnosis_name", "center_detail__name"]
    def perform_create(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        if request.query_params.get("list_format") == "true":
            return Response([serializer.data])  # List-wrapped
        return Response(serializer.data)  # Normal

    def perform_update(self, serializer):
        user = self.request.user
        if not user.center_detail:
            raise ValidationError("User does not have an associated center.")
        serializer.save(center_detail=user.center_detail)
