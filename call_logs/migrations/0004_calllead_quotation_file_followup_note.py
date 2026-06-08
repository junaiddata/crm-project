from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('call_logs', '0003_calllead'),
    ]

    operations = [
        migrations.RemoveField(model_name='calllead', name='quotation'),
        migrations.AddField(
            model_name='calllead', name='quotation_file',
            field=models.FileField(blank=True, null=True, upload_to='quotations/'),
        ),
        migrations.AddField(
            model_name='calllead', name='quotation_filename',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='calllead', name='follow_up_note',
            field=models.TextField(blank=True),
        ),
    ]
