from django.core.management.base import BaseCommand
from leads.models import Lead


SAMPLE_LEADS = [
    {'date': '2026-06-01', 'mobile_no': '54 264 2489', 'email_id': 'sample1@gmail.com', 'name': 'Airo Star Technical Services LLC', 'platform': 'Whatsapp', 'items': 'Ariston Boiler /Copper Pipes & Fittings', 'sales_person': 'AIJAZ', 'quotation': '', 'lead_status': ''},
    {'date': '2026-06-01', 'mobile_no': '50 149 4558', 'email_id': 'sample2@gmail.com', 'name': 'AL ZAIN GENERAL TRADING LLC', 'platform': 'Whatsapp', 'items': 'ARISTON WATER HEATER 50LTR', 'sales_person': 'MUSHARAF', 'quotation': '930 AED', 'quotation_date': '2026-06-02', 'follow_up1_date': '2026-06-05', 'follow_up1_notes': 'Confirmed order', 'lead_status': 'Approved'},
    {'date': '2026-06-01', 'mobile_no': '52 755 9014', 'email_id': 'sample3@gmail.com', 'name': 'Manarat Al Falah', 'platform': 'Whatsapp', 'items': 'Ariston PRO1R 50L - 60 pcs/ 80L - 25 pcs', 'sales_person': 'AIJAZ', 'quotation': '', 'lead_status': ''},
    {'date': '2026-06-02', 'mobile_no': '56 164 6536', 'email_id': 'sample4@gmail.com', 'name': 'Meraj', 'platform': 'Whatsapp', 'items': 'Pipes and fittings enquiry', 'sales_person': 'AIJAZ', 'quotation': '', 'lead_status': ''},
    {'date': '2026-06-02', 'mobile_no': '50 739 0668', 'email_id': 'sample5@gmail.com', 'name': 'Merin from Fastline', 'platform': 'Whatsapp', 'items': 'Cosmoplast UPVC Elbo/ RR Socket/RR-Branch', 'sales_person': 'AIJAZ', 'quotation': '', 'follow_up1_date': '2026-06-07', 'follow_up1_notes': 'Send catalog', 'lead_status': ''},
    {'date': '2026-06-02', 'mobile_no': '56 447 5788', 'email_id': 'sample6@gmail.com', 'name': 'Sabik Salam', 'platform': 'Whatsapp', 'items': 'Pegler Pin 16 Threaded 4" Foot Valve', 'sales_person': 'AIJAZ', 'quotation': '', 'lead_status': ''},
    {'date': '2026-06-03', 'mobile_no': '56 779 8827', 'email_id': 'sample7@gmail.com', 'name': 'Prioritize LLC', 'platform': 'Whatsapp', 'items': 'UPVC pipes/ elbo/socket/ ariston water heater', 'sales_person': 'AIJAZ', 'quotation': '', 'lead_status': ''},
    {'date': '2026-06-03', 'mobile_no': '50 659 1763', 'email_id': 'sample8@gmail.com', 'name': 'Muhammad Tariq', 'platform': 'Whatsapp', 'items': 'Lamborghini 100L Water Heater', 'sales_person': 'MUSHARAF', 'quotation': '', 'lead_status': 'Price too high'},
    {'date': '2026-06-03', 'mobile_no': '56 404 6635', 'email_id': 'sample9@gmail.com', 'name': 'HAKKIM Regnum Contracting', 'platform': 'Whatsapp', 'items': 'Automatic Flow Limiting Valve AFL Brand - Arrow Valves', 'sales_person': 'AIJAZ', 'quotation': '', 'lead_status': ''},
    {'date': '2026-06-04', 'mobile_no': '55 812 3340', 'email_id': 'sample10@gmail.com', 'name': 'Golden Bay Trading', 'platform': 'Email', 'items': 'PPR Pipes & Fittings', 'sales_person': 'RAFIQ', 'quotation': '2,450 AED', 'quotation_date': '2026-06-04', 'follow_up1_date': '2026-06-06', 'follow_up1_notes': 'Waiting for PO', 'lead_status': 'Approved'},
    {'date': '2026-06-05', 'mobile_no': '52 339 1120', 'email_id': 'sample11@gmail.com', 'name': 'Desert Cool HVAC', 'platform': 'Phone Call', 'items': 'Solar Water Heater', 'sales_person': 'SIYAB', 'quotation': '', 'lead_status': 'Rejected'},
    {'date': '2026-06-05', 'mobile_no': '', 'email_id': 'sample12@gmail.com', 'name': 'Khaleej Plumbing', 'platform': 'Website', 'items': 'Copper Fittings', 'sales_person': 'MUZAIN', 'quotation': '', 'lead_status': 'Will Buy in Future'},
]


class Command(BaseCommand):
    help = 'Seed the database with sample CRM lead data'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing leads before seeding')

    def handle(self, *args, **options):
        if options['clear']:
            count = Lead.objects.count()
            Lead.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {count} existing leads'))

        created = 0
        for data in SAMPLE_LEADS:
            Lead.objects.create(**data)
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully created {created} sample leads'))
