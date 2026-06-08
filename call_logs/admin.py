from django.contrib import admin
from .models import CallLog, CallLead


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display    = ('caller_number', 'received_by', 'direction', 'status', 'duration', 'timestamp')
    list_filter     = ('status', 'direction', 'received_by', 'timestamp')
    search_fields   = ('caller_number', 'received_by')
    readonly_fields = ('timestamp',)
    ordering        = ('-timestamp',)


@admin.register(CallLead)
class CallLeadAdmin(admin.ModelAdmin):
    list_display    = ('caller_number', 'call_status', 'lead_status', 'return_called', 'follow_up', 'call_time')
    list_filter     = ('call_status', 'lead_status', 'return_called')
    search_fields   = ('caller_number', 'query', 'quotation')
    readonly_fields = ('created_at', 'updated_at', 'call_time')
    ordering        = ('-call_time',)
