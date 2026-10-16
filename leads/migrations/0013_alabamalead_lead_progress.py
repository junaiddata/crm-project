from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0012_lead_quotation_uploaded_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='alabamalead',
            name='lead_progress',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
