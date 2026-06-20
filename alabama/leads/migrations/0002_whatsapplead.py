from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WhatsAppLead',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sender', models.CharField(max_length=30)),
                ('message_id', models.CharField(max_length=255, unique=True)),
                ('text_body', models.TextField()),
                ('received_at', models.DateTimeField(auto_now_add=True)),
                ('replied', models.BooleanField(default=False)),
                ('reply_text', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-received_at'],
            },
        ),
    ]
