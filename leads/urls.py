from django.urls import path
from . import views

urlpatterns = [
    path('leads/', views.LeadListCreateView.as_view(), name='lead-list-create'),
    path('leads/<int:pk>/', views.LeadDetailView.as_view(), name='lead-detail'),
    path('leads/<int:pk>/upload/', views.LeadUploadView.as_view(), name='lead-upload'),
    path('salespeople/', views.SalespersonListView.as_view(), name='salespeople'),
    path('webhook/whatsapp/', views.whatsapp_webhook, name='whatsapp-webhook'),
    path('whatsapp/<int:pk>/reply/', views.whatsapp_reply, name='whatsapp-reply'),
    path('whatsapp/chat/<str:sender>/send/', views.whatsapp_chat_send, name='whatsapp-chat-send'),
    path('whatsapp/chat/<str:sender>/send-media/', views.whatsapp_chat_send_media, name='whatsapp-chat-send-media'),
]
