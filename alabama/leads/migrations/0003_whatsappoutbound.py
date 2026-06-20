from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0002_whatsapplead'),
    ]

    operations = [
        migrations.CreateModel(
            name='WhatsAppOutbound',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient', models.CharField(max_length=30)),
                ('text_body', models.TextField()),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['sent_at'],
            },
        ),
    ]
