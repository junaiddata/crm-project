from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('call_logs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='calllog',
            name='direction',
            field=models.CharField(
                choices=[('incoming', 'Incoming'), ('outgoing', 'Outgoing')],
                default='incoming',
                max_length=10,
            ),
        ),
    ]
