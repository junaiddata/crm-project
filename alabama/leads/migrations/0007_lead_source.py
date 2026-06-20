from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0006_whatsapplead_sender_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='source',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
