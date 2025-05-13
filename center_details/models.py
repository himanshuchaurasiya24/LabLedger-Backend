from django.db import models

class CenterDetail(models.Model):
    center_name = models.CharField(max_length=30, blank=True, null=True)
    address = models.CharField(max_length=50,blank=True, null= True)
    owner_name = models.CharField(max_length=30, blank=True, null=True)
    owner_phone= models.CharField(max_length=15, blank=True, null=True, unique=True)


    def __str__(self):
        return self.center_name
