from django.db import models

class CenterDetail(models.Model):
    center_name = models.CharField(max_length=30)
    address = models.CharField(max_length=50)
    owner_name = models.CharField(max_length=30)
    owner_phone= models.CharField(max_length=15, unique=True)
    def __str__(self):
        return self.center_name