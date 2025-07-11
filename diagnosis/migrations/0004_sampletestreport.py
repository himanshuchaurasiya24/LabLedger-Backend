# Generated by Django 5.2.1 on 2025-06-04 04:49

import diagnosis.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('center_detail', '0001_initial'),
        ('diagnosis', '0003_alter_bill_test_done_by'),
    ]

    operations = [
        migrations.CreateModel(
            name='SampleTestReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('diagnosis_name', models.CharField(max_length=255)),
                ('sample_report_file', models.FileField(upload_to=diagnosis.models.sample_report_file_upload_path)),
                ('center_detail', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='center_detail_sample_test_report', to='center_detail.centerdetail')),
                ('diagnosis_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sample_test_report', to='diagnosis.diagnosistype')),
            ],
        ),
    ]
