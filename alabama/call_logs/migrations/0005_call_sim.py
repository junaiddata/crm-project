from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('call_logs', '0004_calllead_quotation_file_followup_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='calllog', name='sim',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='calllead', name='sim',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
