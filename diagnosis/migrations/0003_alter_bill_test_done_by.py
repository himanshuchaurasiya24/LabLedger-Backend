# Generated by Django 5.2.1 on 2025-06-03 16:31

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diagnosis', '0002_rename_report_patientreport_alter_bill_bill_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='bill',
            name='test_done_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='test_done_by', to=settings.AUTH_USER_MODEL),
        ),
    ]
