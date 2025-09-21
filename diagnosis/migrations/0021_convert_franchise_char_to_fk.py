# your_app/migrations/00XX_convert_franchise_char_to_fk.py

from django.db import migrations, models
import django.db.models.deletion

def transfer_franchise_data(apps, schema_editor):
    """
    Reads the text from the old 'franchise_name' field,
    finds the matching 'FranchiseName' object, and links them.
    """
    Bill = apps.get_model('diagnosis', 'Bill')
    FranchiseName = apps.get_model('diagnosis', 'FranchiseName')
    
    for bill in Bill.objects.filter(franchise_name__isnull=False).exclude(franchise_name=''):
        
        # ✅ Get the center_detail from the current bill
        center_detail_obj = bill.center_detail
        
        # Use get_or_create with the required center_detail in the defaults
        franchise_obj, created = FranchiseName.objects.get_or_create(
            franchise_name=bill.franchise_name,
            # ✅ Pass the center_detail object here
            center_detail=center_detail_obj,
            defaults={
                'address': 'Address Unknown', 
                'phone_number': '0000000000'
            }
        )
        
        if created:
            print(f"Created new franchise '{bill.franchise_name}' for center '{center_detail_obj}'.")

        bill.franchise_fk = franchise_obj
        bill.save(update_fields=['franchise_fk'])

class Migration(migrations.Migration):

    dependencies = [
        ('diagnosis', '0020_alter_diagnosistype_category_and_more'), # Make sure this matches your previous migration file
    ]

    operations = [
        # 1. Add the new ForeignKey field with a temporary name ('franchise_fk').
        #    It must be nullable to exist alongside the old field temporarily.
        migrations.AddField(
            model_name='bill',
            name='franchise_fk',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='diagnosis.franchisename'
            ),
        ),

        # 2. Run our custom Python function to move the data across.
        migrations.RunPython(transfer_franchise_data, migrations.RunPython.noop),

        # 3. Remove the old CharField.
        migrations.RemoveField(
            model_name='bill',
            name='franchise_name',
        ),

        # 4. Rename the temporary ForeignKey to the final, correct name.
        migrations.RenameField(
            model_name='bill',
            old_name='franchise_fk',
            new_name='franchise_name',
        ),
    ]