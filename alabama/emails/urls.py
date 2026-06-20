from django.urls import path

from . import views

urlpatterns = [
    path('emails/fetch-now/', views.email_fetch_now, name='email-fetch-now'),
    path('emails/<int:pk>/mark/', views.email_mark, name='email-mark'),
    path('emails/thread/<str:address>/send/', views.email_thread_send, name='email-thread-send'),
]
