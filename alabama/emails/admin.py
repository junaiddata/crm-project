from django.contrib import admin

from .models import EmailAttachment, EmailLog, EmailSettings


class EmailAttachmentInline(admin.TabularInline):
    model = EmailAttachment
    extra = 0


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['counterpart', 'counterpart_name', 'direction', 'subject', 'received_at', 'replied']
    list_filter = ['direction', 'replied']
    search_fields = ['counterpart', 'counterpart_name', 'subject', 'body', 'message_id']
    ordering = ['-received_at']
    inlines = [EmailAttachmentInline]


@admin.register(EmailSettings)
class EmailSettingsAdmin(admin.ModelAdmin):
    list_display = ['email_address', 'imap_host', 'smtp_host', 'enabled', 'last_fetch_at', 'last_fetch_info']
