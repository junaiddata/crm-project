from django.contrib import admin
from .models import Lead, WhatsAppLead, AlabamaLead, AlabamaWhatsAppLead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'date', 'platform', 'sales_person', 'lead_status', 'created_at']
    list_filter = ['lead_status', 'platform', 'sales_person']
    search_fields = ['name', 'email_id', 'mobile_no', 'items']
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']


@admin.register(WhatsAppLead)
class WhatsAppLeadAdmin(admin.ModelAdmin):
    list_display = ['sender', 'sender_name', 'msg_type', 'text_body', 'media_name', 'received_at', 'replied']
    list_filter = ['replied', 'msg_type']
    search_fields = ['sender', 'sender_name', 'text_body', 'message_id', 'media_name']
    readonly_fields = ['sender', 'sender_name', 'message_id', 'text_body', 'msg_type', 'media_file', 'media_name', 'received_at']
    ordering = ['-received_at']


@admin.register(AlabamaLead)
class AlabamaLeadAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'date', 'platform', 'sales_person', 'lead_status', 'created_at']
    list_filter = ['lead_status', 'platform', 'sales_person']
    search_fields = ['name', 'email_id', 'mobile_no', 'items']
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']


@admin.register(AlabamaWhatsAppLead)
class AlabamaWhatsAppLeadAdmin(admin.ModelAdmin):
    list_display = ['sender', 'sender_name', 'msg_type', 'text_body', 'media_name', 'received_at', 'replied']
    list_filter = ['replied', 'msg_type']
    search_fields = ['sender', 'sender_name', 'text_body', 'message_id', 'media_name']
    readonly_fields = ['sender', 'sender_name', 'message_id', 'text_body', 'msg_type', 'media_file', 'media_name', 'received_at']
    ordering = ['-received_at']
