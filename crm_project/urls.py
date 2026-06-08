from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

from leads.views import whatsapp_dashboard, mark_replied, whatsapp_chat
from call_logs.views import calls_dashboard, call_leads_dashboard


def landing(request):
    return render(request, 'landing.html')


def crm_index(request):
    return render(request, 'crm/index.html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('leads.urls')),
    path('api/', include('call_logs.urls')),
    path('crm/', crm_index, name='crm'),
    path('whatsapp/', whatsapp_dashboard, name='whatsapp-dashboard'),
    path('whatsapp/<int:pk>/reply/', mark_replied, name='mark-replied'),
    path('whatsapp/chat/<str:sender>/', whatsapp_chat, name='whatsapp-chat'),
    path('calls/', calls_dashboard, name='calls-dashboard'),
    path('call-leads/', call_leads_dashboard, name='call-leads'),
    path('', landing, name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
