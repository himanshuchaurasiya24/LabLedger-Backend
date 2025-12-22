"""
Script to populate initial diagnosis categories in the database.
Run this after migrations: python manage.py shell < populate_categories.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LabLedger.settings')
django.setup()

from diagnosis.models import DiagnosisCategory

# Define initial categories
categories_data = [
    {'name': 'Ultrasound', 'description': 'Ultrasound diagnostic tests', 'is_franchise_lab': False},
    {'name': 'Pathology', 'description': 'Pathology and laboratory tests', 'is_franchise_lab': False},
    {'name': 'ECG', 'description': 'Electrocardiogram tests', 'is_franchise_lab': False},
    {'name': 'X-Ray', 'description': 'X-Ray imaging', 'is_franchise_lab': False},
    {'name': 'Franchise Lab', 'description': 'Franchise laboratory tests', 'is_franchise_lab': True},
    {'name': 'Others', 'description': 'Other diagnostic tests', 'is_franchise_lab': False},
]

print("Creating initial diagnosis categories...")
for cat_data in categories_data:
    category, created = DiagnosisCategory.objects.get_or_create(
        name=cat_data['name'],
        defaults={
            'description': cat_data['description'],
            'is_franchise_lab': cat_data['is_franchise_lab'],
            'is_active': True
        }
    )
    if created:
        print(f"✓ Created: {cat_data['name']}")
    else:
        print(f"- Already exists: {cat_data['name']}")

print("\nDone! Created {} categories.".format(DiagnosisCategory.objects.count()))
