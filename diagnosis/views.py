from django.shortcuts import render
from rest_framework import viewsets,permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import *
from .serializers import *



class BillViewset(viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class= BillSerializer
    authentication_classes= [JWTAuthentication]
    permission_classes= [permissions.IsAuthenticated]