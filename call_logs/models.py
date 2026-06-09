from django.db import models
from django.utils import timezone


class CallLog(models.Model):
    STATUS_CHOICES = [
        ('answered', 'Answered'),
        ('missed',   'Missed'),
        ('rejected', 'Rejected'),
    ]
    DIRECTION_CHOICES = [
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
    ]

    caller_number = models.CharField(max_length=50)
    received_by   = models.CharField(max_length=100)
    sim           = models.CharField(max_length=100, blank=True, default='')   # which SIM handled the call (per-SIM label)
    direction     = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default='incoming')
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES)
    duration      = models.IntegerField(default=0)
    timestamp     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.caller_number} → {self.received_by} [{self.status}]'


class CallLead(models.Model):
    LEAD_STATUS = [
        ('active',      'Active'),
        ('junk',        'Junk'),
        ('irrelevant',  'Irrelevant'),
    ]

    call_log      = models.OneToOneField(CallLog, on_delete=models.CASCADE, related_name='lead')
    caller_number = models.CharField(max_length=50)
    call_status   = models.CharField(max_length=20)   # answered / missed / rejected
    duration      = models.IntegerField(default=0)
    call_time     = models.DateTimeField()
    received_by   = models.CharField(max_length=100, blank=True)
    sim           = models.CharField(max_length=100, blank=True, default='')

    # Lead fields (editable by staff)
    query              = models.TextField(blank=True)
    quotation_file     = models.FileField(upload_to='quotations/', blank=True, null=True)
    quotation_filename = models.CharField(max_length=255, blank=True)
    follow_up          = models.DateField(null=True, blank=True)
    follow_up_note     = models.TextField(blank=True)
    notes              = models.TextField(blank=True)

    # Missed call tracking
    return_called    = models.BooleanField(default=False)
    return_called_at = models.DateTimeField(null=True, blank=True)

    # Lead management
    lead_status = models.CharField(max_length=20, choices=LEAD_STATUS, default='active')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-call_time']

    def __str__(self):
        return f'Lead: {self.caller_number} [{self.call_status}]'
