from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CallLog',
            fields=[
                ('id',            models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('caller_number', models.CharField(max_length=50)),
                ('received_by',   models.CharField(max_length=100)),
                ('status',        models.CharField(choices=[('answered', 'Answered'), ('missed', 'Missed'), ('rejected', 'Rejected')], max_length=20)),
                ('duration',      models.IntegerField(default=0)),
                ('timestamp',     models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]
