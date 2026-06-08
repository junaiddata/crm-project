from django.urls import path
from .views import (
    LogCallView, CallLogListView,
    update_call_lead, toggle_return_called, set_lead_status,
)

urlpatterns = [
    path('calls/log/',                          LogCallView.as_view(),    name='call-log'),
    path('calls/',                              CallLogListView.as_view(), name='call-list'),
    path('call-leads/<int:pk>/update/',         update_call_lead,         name='call-lead-update'),
    path('call-leads/<int:pk>/return-called/',  toggle_return_called,     name='call-lead-return'),
    path('call-leads/<int:pk>/status/',         set_lead_status,          name='call-lead-status'),
]
