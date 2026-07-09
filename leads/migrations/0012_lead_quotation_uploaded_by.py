# Adds "quotation uploaded by" to Lead / AlabamaLead — the name of the person
# who uploaded the quotation (set once from the CRM, then locked).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0011_alabamabroadcastjob_alabamalead_alabamawhatsapplead_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='quotation_uploaded_by',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='alabamalead',
            name='quotation_uploaded_by',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
