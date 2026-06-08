from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('call_logs', '0002_calllog_direction'),
    ]

    operations = [
        migrations.CreateModel(
            name='CallLead',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('call_log', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='lead', to='call_logs.calllog')),
                ('caller_number', models.CharField(max_length=50)),
                ('call_status',   models.CharField(max_length=20)),
                ('duration',      models.IntegerField(default=0)),
                ('call_time',     models.DateTimeField()),
                ('received_by',   models.CharField(blank=True, max_length=100)),
                ('query',         models.TextField(blank=True)),
                ('quotation',     models.CharField(blank=True, max_length=200)),
                ('follow_up',     models.DateField(blank=True, null=True)),
                ('notes',         models.TextField(blank=True)),
                ('return_called',    models.BooleanField(default=False)),
                ('return_called_at', models.DateTimeField(blank=True, null=True)),
                ('lead_status',   models.CharField(choices=[('active','Active'),('junk','Junk'),('irrelevant','Irrelevant')], default='active', max_length=20)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('updated_at',    models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-call_time']},
        ),
    ]
