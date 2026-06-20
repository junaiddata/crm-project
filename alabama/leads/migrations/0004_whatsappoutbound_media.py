from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0003_whatsappoutbound'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappoutbound',
            name='msg_type',
            field=models.CharField(
                choices=[('text','Text'),('image','Image'),('document','Document'),('video','Video'),('audio','Audio')],
                default='text',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='whatsappoutbound',
            name='media_file',
            field=models.FileField(blank=True, null=True, upload_to='whatsapp_outbound/'),
        ),
        migrations.AddField(
            model_name='whatsappoutbound',
            name='media_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='whatsappoutbound',
            name='text_body',
            field=models.TextField(blank=True),
        ),
    ]
