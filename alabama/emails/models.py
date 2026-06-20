from django.db import models
from django.utils import timezone


class EmailSettings(models.Model):
    """Singleton — IMAP/SMTP credentials for the sales mailbox, editable at /emails/settings/."""

    email_address = models.EmailField(blank=True)
    display_name  = models.CharField(max_length=255, blank=True)
    # App password (if the provider uses 2FA) or mailbox password. Stored in the
    # server DB so it can be managed from the settings page instead of .env.
    password      = models.CharField(max_length=255, blank=True)

    imap_host    = models.CharField(max_length=255, blank=True)
    imap_port    = models.PositiveIntegerField(default=993)
    smtp_host    = models.CharField(max_length=255, blank=True)
    smtp_port    = models.PositiveIntegerField(default=465)
    # On → implicit SSL (port 465). Off → STARTTLS (port 587).
    smtp_use_ssl = models.BooleanField(default=True)

    enabled         = models.BooleanField(default=False)
    # On the very first sync, ignore mail older than this (default: last 30 days).
    fetch_since     = models.DateField(null=True, blank=True)
    last_fetch_at   = models.DateTimeField(null=True, blank=True)
    last_fetch_info = models.CharField(max_length=255, blank=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Email settings'
        verbose_name_plural = 'Email settings'

    def __str__(self):
        return self.email_address or 'Email settings (not configured)'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def is_configured(self):
        return bool(self.email_address and self.password and self.imap_host and self.smtp_host)


class EmailLog(models.Model):
    DIRECTIONS = [('in', 'Incoming'), ('out', 'Outgoing')]

    direction        = models.CharField(max_length=3, choices=DIRECTIONS, default='in')
    # The customer's address: sender for inbound, recipient for outbound.
    counterpart      = models.CharField(max_length=255)
    counterpart_name = models.CharField(max_length=255, blank=True)
    subject          = models.TextField(blank=True)
    body             = models.TextField(blank=True)
    message_id       = models.CharField(max_length=512, unique=True)
    in_reply_to      = models.CharField(max_length=512, blank=True)
    # Date header for inbound, send time for outbound.
    received_at      = models.DateTimeField(default=timezone.now)
    replied          = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        arrow = '←' if self.direction == 'in' else '→'
        return f'{arrow} {self.counterpart} — {self.subject[:60]}'


class EmailAttachment(models.Model):
    email        = models.ForeignKey(EmailLog, on_delete=models.CASCADE, related_name='attachments')
    file         = models.FileField(upload_to='email_attachments/')
    filename     = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    size         = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.filename or f'Attachment #{self.pk}'
