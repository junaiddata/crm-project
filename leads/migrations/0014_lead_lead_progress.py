from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0013_alabamalead_lead_progress'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='lead_progress',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
