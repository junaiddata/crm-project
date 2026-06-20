"""
One-off cleanup for messages that show twice in the chat view.

Older chat-sent messages were stored BOTH as a WhatsAppOutbound record and
as `reply_text` on the incoming WhatsAppLead, so they render twice. This
clears the redundant `reply_text` ONLY where a matching outbound exists
(or it's a media "[Sent …]" marker). Dashboard Quick Replies — which have
no outbound record — are left untouched. `replied` status is preserved.

Usage:
    python manage.py dedupe_whatsapp_replies --dry-run   # preview
    python manage.py dedupe_whatsapp_replies             # apply
"""
from django.core.management.base import BaseCommand

from leads.models import WhatsAppLead, WhatsAppOutbound


class Command(BaseCommand):
    help = 'Clear redundant reply_text that duplicates an outbound message in the chat.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be cleared without changing anything.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        leads = WhatsAppLead.objects.exclude(reply_text='')
        cleared = 0
        kept    = 0

        for lead in leads:
            text = lead.reply_text

            # Media chat-sends were stored as "[Sent image: file.jpg]" — always
            # have a matching outbound record, so always safe to clear.
            is_media_marker = text.startswith('[Sent ')

            has_outbound = is_media_marker or WhatsAppOutbound.objects.filter(
                recipient=lead.sender, text_body=text,
            ).exists()

            if not has_outbound:
                kept += 1  # genuine Quick Reply (no outbound) — keep it
                continue

            if dry_run:
                self.stdout.write(f'  [dry-run] would clear reply on lead #{lead.id} ({lead.sender}): {text[:50]!r}')
            else:
                lead.reply_text = ''
                lead.save(update_fields=['reply_text'])
            cleared += 1

        verb = 'Would clear' if dry_run else 'Cleared'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} {cleared} duplicate repl{"y" if cleared == 1 else "ies"}; '
            f'kept {kept} Quick Repl{"y" if kept == 1 else "ies"}.'
        ))
