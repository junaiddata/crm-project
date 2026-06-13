from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.http import FileResponse, Http404

from leads.views import whatsapp_dashboard, mark_replied, whatsapp_chat
from call_logs.views import calls_dashboard, call_leads_dashboard
from emails.views import email_dashboard, email_thread, email_settings_page


APK_PATH = settings.BASE_DIR / 'downloads' / 'CallTracker.apk'


def landing(request):
    return render(request, 'landing.html')


@login_required
def crm_index(request):
    return render(request, 'crm/index.html')


def download_page(request):
    apk_size = None
    if APK_PATH.exists():
        apk_size = round(APK_PATH.stat().st_size / (1024 * 1024), 1)
    download_url = request.build_absolute_uri('/download/app/')
    return render(request, 'download.html', {'apk_size': apk_size, 'download_url': download_url})


def download_apk(request):
    if not APK_PATH.exists():
        raise Http404('APK file not found on server.')
    return FileResponse(open(APK_PATH, 'rb'), as_attachment=True, filename='CallTracker.apk')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/',  auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('api/', include('leads.urls')),
    path('api/', include('call_logs.urls')),
    path('api/', include('emails.urls')),
    path('crm/', crm_index, name='crm'),
    path('download/', download_page, name='download'),
    path('download/app/', download_apk, name='download-apk'),
    path('whatsapp/', whatsapp_dashboard, name='whatsapp-dashboard'),
    path('whatsapp/<int:pk>/reply/', mark_replied, name='mark-replied'),
    path('whatsapp/chat/<str:sender>/', whatsapp_chat, name='whatsapp-chat'),
    path('emails/', email_dashboard, name='email-dashboard'),
    path('emails/settings/', email_settings_page, name='email-settings'),
    path('emails/thread/<str:address>/', email_thread, name='email-thread'),
    path('calls/', calls_dashboard, name='calls-dashboard'),
    path('call-leads/', call_leads_dashboard, name='call-leads'),
    path('', landing, name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
