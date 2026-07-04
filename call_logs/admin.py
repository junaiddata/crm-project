from django.contrib import admin
from .models import (
    CallLog, CallLead, AlabamaCallLog, AlabamaCallLead,
    ExcludedNumber, AlabamaExcludedNumber,
)


@admin.register(ExcludedNumber)
class ExcludedNumberAdmin(admin.ModelAdmin):
    list_display  = ('number', 'note', 'created_at')
    search_fields = ('number', 'note')
    ordering      = ('-created_at',)


@admin.register(AlabamaExcludedNumber)
class AlabamaExcludedNumberAdmin(admin.ModelAdmin):
    list_display  = ('number', 'note', 'created_at')
    search_fields = ('number', 'note')
    ordering      = ('-created_at',)


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display    = ('caller_number', 'received_by', 'sim', 'direction', 'status', 'duration', 'timestamp')
    list_filter     = ('status', 'direction', 'received_by', 'sim', 'timestamp')
    search_fields   = ('caller_number', 'received_by', 'sim')
    readonly_fields = ('timestamp',)
    ordering        = ('-timestamp',)


@admin.register(CallLead)
class CallLeadAdmin(admin.ModelAdmin):
    list_display    = ('caller_number', 'call_status', 'lead_status', 'return_called', 'follow_up', 'call_time')
    list_filter     = ('call_status', 'lead_status', 'return_called')
    search_fields   = ('caller_number', 'query', 'quotation')
    readonly_fields = ('created_at', 'updated_at', 'call_time')
    ordering        = ('-call_time',)


@admin.register(AlabamaCallLog)
class AlabamaCallLogAdmin(admin.ModelAdmin):
    list_display    = ('caller_number', 'received_by', 'sim', 'direction', 'status', 'duration', 'timestamp')
    list_filter     = ('status', 'direction', 'received_by', 'sim', 'timestamp')
    search_fields   = ('caller_number', 'received_by', 'sim')
    readonly_fields = ('timestamp',)
    ordering        = ('-timestamp',)


@admin.register(AlabamaCallLead)
class AlabamaCallLeadAdmin(admin.ModelAdmin):
    list_display    = ('caller_number', 'call_status', 'lead_status', 'return_called', 'follow_up', 'call_time')
    list_filter     = ('call_status', 'lead_status', 'return_called')
    search_fields   = ('caller_number', 'query', 'quotation')
    readonly_fields = ('created_at', 'updated_at', 'call_time')
    ordering        = ('-call_time',)
