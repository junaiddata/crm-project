from django.db import models


class WhatsAppLead(models.Model):
    MSG_TYPES = [
        ('text',     'Text'),
        ('image',    'Image'),
        ('document', 'Document'),
        ('video',    'Video'),
        ('audio',    'Audio'),
    ]

    sender      = models.CharField(max_length=30)
    sender_name = models.CharField(max_length=255, blank=True)
    message_id  = models.CharField(max_length=255, unique=True)
    text_body   = models.TextField(blank=True)
    msg_type    = models.CharField(max_length=20, default='text', choices=MSG_TYPES)
    media_file  = models.FileField(upload_to='whatsapp_inbound/', blank=True, null=True)
    media_name  = models.CharField(max_length=255, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    replied     = models.BooleanField(default=False)
    reply_text  = models.TextField(blank=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        if self.msg_type != 'text':
            return f'{self.sender} — [{self.msg_type}] {self.media_name or ""}'
        return f'{self.sender} — {self.text_body[:60]}'


class Lead(models.Model):
    date             = models.DateField()
    mobile_no        = models.CharField(max_length=30, blank=True)
    email_id         = models.CharField(max_length=255, blank=True)
    name             = models.CharField(max_length=255, blank=True)
    platform         = models.CharField(max_length=50, blank=True)
    items            = models.TextField(blank=True)
    sales_person     = models.CharField(max_length=100, blank=True)
    quotation        = models.CharField(max_length=100, blank=True)
    quotation_file   = models.FileField(upload_to='quotations/', blank=True, null=True)
    quotation_date   = models.DateField(null=True, blank=True)
    follow_up1_date  = models.DateField(null=True, blank=True)
    follow_up1_notes = models.TextField(blank=True)
    follow_up2_date  = models.DateField(null=True, blank=True)
    follow_up2_notes = models.TextField(blank=True)
    lead_status      = models.CharField(max_length=50, blank=True)
    source           = models.CharField(max_length=20, blank=True)  # e.g. 'whatsapp' when auto-added
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return self.name or f'Lead #{self.pk}'


class WhatsAppOutbound(models.Model):
    MSG_TYPES = [
        ('text',     'Text'),
        ('image',    'Image'),
        ('document', 'Document'),
        ('video',    'Video'),
        ('audio',    'Audio'),
    ]

    recipient  = models.CharField(max_length=30)
    msg_type   = models.CharField(max_length=20, default='text', choices=MSG_TYPES)
    text_body  = models.TextField(blank=True)
    media_file = models.FileField(upload_to='whatsapp_outbound/', blank=True, null=True)
    media_name = models.CharField(max_length=255, blank=True)
    sent_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        return f'To {self.recipient} [{self.msg_type}] — {self.text_body[:60] or self.media_name}'
