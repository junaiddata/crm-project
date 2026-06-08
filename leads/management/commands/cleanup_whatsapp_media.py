"""
Delete WhatsApp media files (inbound + outbound) older than N days to keep
the server disk from filling up. The message records are kept — only the
file on disk is removed and the media_file field is cleared, so the chat
still shows the message as "media expired".

Usage:
    python manage.py cleanup_whatsapp_media            # default 30 days
    python manage.py cleanup_whatsapp_media --days 60
    python manage.py cleanup_whatsapp_media --dry-run   # show what would be deleted
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from leads.models import WhatsAppLead, WhatsAppOutbound


class Command(BaseCommand):
    help = 'Delete WhatsApp media files older than N days (default 30) to free server space.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30,
                            help='Delete media older than this many days (default: 30).')
        parser.add_argument('--dry-run', action='store_true',
                            help='List files that would be deleted without deleting them.')

    def handle(self, *args, **options):
        days     = options['days']
        dry_run  = options['dry_run']
        cutoff   = timezone.now() - timedelta(days=days)

        self.stdout.write(f'Cutoff: deleting media older than {days} days (before {cutoff:%Y-%m-%d %H:%M}).')

        targets = [
            ('inbound',  WhatsAppLead.objects.filter(received_at__lt=cutoff).exclude(media_file='')),
            ('outbound', WhatsAppOutbound.objects.filter(sent_at__lt=cutoff).exclude(media_file='')),
        ]

        total_deleted = 0
        total_bytes   = 0

        for label, qs in targets:
            for obj in qs:
                if not obj.media_file:
                    continue
                name = obj.media_file.name
                try:
                    size = obj.media_file.size
                except (OSError, ValueError):
                    size = 0  # file already gone from disk

                if dry_run:
                    self.stdout.write(f'  [dry-run] {label}: would delete {name} ({self._fmt(size)})')
                else:
                    obj.media_file.delete(save=False)   # remove file from storage
                    obj.media_file = None
                    obj.save(update_fields=['media_file'])
                    self.stdout.write(f'  {label}: deleted {name} ({self._fmt(size)})')

                total_deleted += 1
                total_bytes   += size

        verb = 'Would free' if dry_run else 'Freed'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} {self._fmt(total_bytes)} across {total_deleted} file(s).'
        ))

    @staticmethod
    def _fmt(b):
        if b < 1024:
            return f'{b} B'
        if b < 1048576:
            return f'{b / 1024:.1f} KB'
        return f'{b / 1048576:.1f} MB'
