from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Lead',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('mobile_no', models.CharField(blank=True, max_length=30)),
                ('email_id', models.CharField(blank=True, max_length=255)),
                ('name', models.CharField(blank=True, max_length=255)),
                ('platform', models.CharField(blank=True, max_length=50)),
                ('items', models.TextField(blank=True)),
                ('sales_person', models.CharField(blank=True, max_length=100)),
                ('quotation', models.CharField(blank=True, max_length=100)),
                ('quotation_file', models.FileField(blank=True, null=True, upload_to='quotations/')),
                ('quotation_date', models.DateField(blank=True, null=True)),
                ('follow_up1_date', models.DateField(blank=True, null=True)),
                ('follow_up1_notes', models.TextField(blank=True)),
                ('follow_up2_date', models.DateField(blank=True, null=True)),
                ('follow_up2_notes', models.TextField(blank=True)),
                ('lead_status', models.CharField(blank=True, max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-date', '-created_at'],
            },
        ),
    ]
