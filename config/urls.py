from django.contrib import admin
from django.urls import path
from campaigns.views import dashboard, create_campaign, ai_suggest_view
# 1. Add this import (make sure you created this view in contacts/views.py earlier)
from contacts.views import upload_contacts 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('campaign/new/', create_campaign, name='create_campaign'),
    path('contacts/upload/', upload_contacts, name='upload_contacts'),
    path('api/ai-suggest/', ai_suggest_view, name='ai_suggest'),
]