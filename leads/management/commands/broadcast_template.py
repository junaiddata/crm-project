"""
Broadcast an approved WhatsApp template to a list of numbers from a CSV.

Outside the 24-hour customer-service window you can only open a conversation
with an *approved template* — this is how marketing "broadcasts" are sent on
the WhatsApp Cloud API. There is no true bulk endpoint; each recipient gets an
individual /messages call, so this command loops and rate-limits.

CSV format: one phone number per row in the FIRST column (international format,
with or without a leading +; spaces/dashes are stripped). A header row like
"phone" or "number" is auto-skipped.

The header image can be supplied three ways:
  --header-image-file PATH   local file, uploaded to Meta once (easiest — no hosting)
  --header-image-url  URL    public HTTPS URL Meta fetches
  --header-image-id   ID     a media id you already uploaded

Examples:
    # Preview only — no messages sent
    python manage.py broadcast_template --csv leads.csv \
        --header-image-file C:/path/to/plumbing.jpg --dry-run

    # Real send of the plumbing_marketing template from +971 54 533 8872
    python manage.py broadcast_template --csv leads.csv \
        --header-image-file C:/path/to/plumbing.jpg

Defaults: template=plumbing_marketing, language=en,
          from=1131190376754791 (+971 54 533 8872).
"""
import csv
import mimetypes
import os
import re
import time

from django.core.management.base import BaseCommand, CommandError

from leads.models import WhatsAppOutbound
from leads.utils import send_whatsapp_template, upload_whatsapp_media

# +971 54 533 8872 — the number we currently receive on.
DEFAULT_PHONE_ID = '1131190376754791'


class Command(BaseCommand):
    help = 'Broadcast an approved WhatsApp template to numbers listed in a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('--csv', required=True,
                            help='Path to CSV file; phone number in the first column.')
        parser.add_argument('--template', default='plumbing_marketing',
                            help='Approved template name (default: plumbing_marketing).')
        parser.add_argument('--language', default='en',
                            help='Template language code (default: en).')
        parser.add_argument('--header-image-file',
                            help='Path to a local image file; uploaded to Meta once, then reused for all sends.')
        parser.add_argument('--header-image-url',
                            help='Public URL for the template header image.')
        parser.add_argument('--header-image-id',
                            help='Already-uploaded Meta media id for the header image.')
        parser.add_argument('--from', dest='phone_id', default=DEFAULT_PHONE_ID,
                            help=f'Sending phone_number_id (default: {DEFAULT_PHONE_ID} = +971 54 533 8872).')
        parser.add_argument('--delay', type=float, default=1.0,
                            help='Seconds to wait between sends (default: 1.0).')
        parser.add_argument('--limit', type=int,
                            help='Only send to the first N numbers (useful for a test run).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Parse the CSV and show what would be sent without sending.')

    def handle(self, *args, **opts):
        numbers = self._read_numbers(opts['csv'])
        if opts.get('limit'):
            numbers = numbers[:opts['limit']]

        if not numbers:
            raise CommandError('No phone numbers found in the CSV.')

        # A local file (--header-image-file) is uploaded once to Meta and the
        # returned media id is reused for every recipient — no public URL needed.
        header_image_id = opts['header_image_id']
        if opts['header_image_file'] and not opts['dry_run']:
            header_image_id = self._upload_header(opts['header_image_file'], opts['phone_id'])

        if not (opts['header_image_url'] or header_image_id or opts['header_image_file']):
            self.stdout.write(self.style.WARNING(
                'No header image given (--header-image-file / --header-image-url / '
                '--header-image-id). The plumbing_marketing template has an image '
                'header, so Meta will likely reject the send. Continue only if you '
                'are sure the template has no media header.'
            ))

        self.stdout.write(
            f'Template "{opts["template"]}" (lang {opts["language"]}) '
            f'from phone id {opts["phone_id"]} -> {len(numbers)} recipient(s).'
        )

        if opts['dry_run']:
            for n in numbers:
                self.stdout.write(f'  [dry-run] would send to {n}')
            self.stdout.write(self.style.SUCCESS(f'Dry run: {len(numbers)} message(s) not sent.'))
            return

        sent = failed = 0
        for i, number in enumerate(numbers, 1):
            msg_id = send_whatsapp_template(
                to_number=number,
                template_name=opts['template'],
                language=opts['language'],
                header_image_url=opts['header_image_url'],
                header_image_id=header_image_id,
                phone_number_id=opts['phone_id'],
            )
            if msg_id:
                sent += 1
                WhatsAppOutbound.objects.create(
                    recipient=number,
                    business_phone_id=opts['phone_id'],
                    msg_type='text',
                    text_body=f'[template: {opts["template"]}]',
                )
                self.stdout.write(self.style.SUCCESS(f'  [{i}/{len(numbers)}] sent -> {number}'))
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f'  [{i}/{len(numbers)}] FAILED -> {number}'))

            if opts['delay'] and i < len(numbers):
                time.sleep(opts['delay'])

        self.stdout.write(self.style.SUCCESS(f'Done. Sent {sent}, failed {failed}.'))

    def _upload_header(self, path, phone_id):
        """Upload a local image to Meta and return its media id (reused for all sends)."""
        if not os.path.exists(path):
            raise CommandError(f'Header image file not found: {path}')

        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type or not mime_type.startswith('image/'):
            raise CommandError(f'Header image must be an image file; got mime {mime_type!r} for {path}.')

        with open(path, 'rb') as f:
            file_bytes = f.read()

        media_id = upload_whatsapp_media(file_bytes, mime_type, os.path.basename(path), phone_id)
        if not media_id:
            raise CommandError('Failed to upload header image to Meta (see logs). Aborting broadcast.')

        self.stdout.write(self.style.SUCCESS(f'Uploaded header image -> media id {media_id}'))
        return media_id

    def _read_numbers(self, path):
        """Return a de-duplicated list of normalized phone numbers from the CSV."""
        seen = set()
        numbers = []
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                for row in csv.reader(f):
                    if not row:
                        continue
                    raw = row[0].strip()
                    digits = re.sub(r'[^\d]', '', raw)
                    # Skip a header row / empty / too-short-to-be-a-number cells.
                    if len(digits) < 8:
                        continue
                    if digits not in seen:
                        seen.add(digits)
                        numbers.append(digits)
        except FileNotFoundError:
            raise CommandError(f'CSV file not found: {path}')
        return numbers
