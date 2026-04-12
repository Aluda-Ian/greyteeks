from django.contrib import admin
from django.urls import path, include
from campaigns.views import dashboard, create_campaign, ai_suggest_view, home_view
from contacts.views import upload_contacts 

urlpatterns = [
    # General Access & Auth
    path('', home_view, name='home'), 
    path('accounts/', include('django.contrib.auth.urls')), 
    
    # Dashboard & Features (Protected by @login_required in views)
    path('dashboard/', dashboard, name='dashboard'),
    path('campaign/new/', create_campaign, name='create_campaign'),
    path('contacts/upload/', upload_contacts, name='upload_contacts'),
    
    # System Admin (Database)
    path('system-admin/', admin.site.urls), # Renamed to avoid confusion with dashboard
    
    # APIs
    path('api/ai-suggest/', ai_suggest_view, name='ai_suggest'),
]