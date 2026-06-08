from django.contrib import admin
from .models import Lead, WhatsAppLead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'date', 'platform', 'sales_person', 'lead_status', 'created_at']
    list_filter = ['lead_status', 'platform', 'sales_person']
    search_fields = ['name', 'email_id', 'mobile_no', 'items']
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']


@admin.register(WhatsAppLead)
class WhatsAppLeadAdmin(admin.ModelAdmin):
    list_display = ['sender', 'text_body', 'received_at', 'replied']
    list_filter = ['replied']
    search_fields = ['sender', 'text_body', 'message_id']
    readonly_fields = ['sender', 'message_id', 'text_body', 'received_at']
    ordering = ['-received_at']
