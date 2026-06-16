"""
Broadcast an approved WhatsApp template to a list of numbers from a CSV.

Outside the 24-hour customer-service window you can only open a conversation
with an *approved template* — this is how marketing "broadcasts" are sent on
the WhatsApp Cloud API. There is no true bulk endpoint; each recipient gets an
individual /messages call, so this command loops and rate-limits.

The actual send/record logic is shared with the web Broadcast page in
`leads/broadcast.py`.

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
import mimetypes
import os
import time

from django.core.management.base import BaseCommand, CommandError

from leads.broadcast import (
    DEFAULT_PHONE_ID, parse_numbers, send_broadcast,
    stage_chat_image, upload_header_image,
)


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
        parser.add_argument('--caption',
                            help='Caption shown under the broadcast in the chat thread '
                                 '(default: "Broadcast: <template>"). Use the template body text '
                                 'so agents can see what each customer received.')
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

        if not (opts['header_image_url'] or opts['header_image_id'] or opts['header_image_file']):
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

        # Resolve the header image: a local file is uploaded to Meta once (and
        # staged for the chat thread); url/id are passed straight through.
        header_image_id = opts['header_image_id']
        chat_media_name = None
        if opts['header_image_file']:
            file_bytes, mime_type, basename = self._read_image(opts['header_image_file'])
            header_image_id = upload_header_image(file_bytes, mime_type, basename, opts['phone_id'])
            if not header_image_id:
                raise CommandError('Failed to upload header image to Meta (see logs). Aborting.')
            self.stdout.write(self.style.SUCCESS(f'Uploaded header image -> media id {header_image_id}'))
            chat_media_name = stage_chat_image(file_bytes, basename)
            self.stdout.write(self.style.SUCCESS(f'Staged chat image -> {chat_media_name}'))

        last = len(numbers)
        delay = opts['delay']

        def on_progress(i, number, ok):
            if ok:
                self.stdout.write(self.style.SUCCESS(f'  [{i}/{last}] sent -> {number}'))
            else:
                self.stdout.write(self.style.ERROR(f'  [{i}/{last}] FAILED -> {number}'))
            if delay and i < last:
                time.sleep(delay)

        result = send_broadcast(
            numbers,
            template=opts['template'],
            language=opts['language'],
            phone_id=opts['phone_id'],
            caption=opts['caption'],
            header_image_id=header_image_id,
            header_image_url=opts['header_image_url'],
            chat_media_name=chat_media_name,
            on_progress=on_progress,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Done. Sent {result["sent"]}, failed {result["failed"]}.'
        ))

    def _read_image(self, path):
        """Read a local image file; return (bytes, mime_type, basename)."""
        if not os.path.exists(path):
            raise CommandError(f'Header image file not found: {path}')
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type or not mime_type.startswith('image/'):
            raise CommandError(f'Header image must be an image file; got mime {mime_type!r} for {path}.')
        with open(path, 'rb') as f:
            return f.read(), mime_type, os.path.basename(path)

    def _read_numbers(self, path):
        """Return de-duplicated, normalized phone numbers from the CSV file."""
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                return parse_numbers(f.read())
        except FileNotFoundError:
            raise CommandError(f'CSV file not found: {path}')
