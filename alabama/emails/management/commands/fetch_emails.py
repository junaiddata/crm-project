from django.core.management.base import BaseCommand

from emails.utils import fetch_emails


class Command(BaseCommand):
    help = 'Fetch new messages from the configured IMAP inbox into EmailLog (run every 3-5 min via cron)'

    def handle(self, *args, **options):
        count, info = fetch_emails()
        style = self.style.SUCCESS if count or info.startswith('Fetched') else self.style.WARNING
        self.stdout.write(style(info))
