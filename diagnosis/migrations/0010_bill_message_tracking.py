from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diagnosis', '0009_reset_pk_sequences'),
    ]

    operations = [
        migrations.AddField(
            model_name='bill',
            name='is_message_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='bill',
            name='message_link_token',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='bill',
            name='message_link_created_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bill',
            name='message_link_used_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
