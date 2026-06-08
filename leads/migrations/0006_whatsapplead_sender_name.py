from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0005_whatsapplead_media'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsapplead',
            name='sender_name',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
