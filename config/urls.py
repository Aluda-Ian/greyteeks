from django.contrib import admin
from django.urls import path, include
# Add ai_suggest_view to this line
from campaigns.views import dashboard, create_campaign, home_view, register_view, ai_suggest_view 
from contacts.views import upload_contacts 

urlpatterns = [
    path('', home_view, name='home'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('register/', register_view, name='register'),
    path('dashboard/', dashboard, name='dashboard'),
    path('campaign/new/', create_campaign, name='create_campaign'),
    path('contacts/upload/', upload_contacts, name='upload_contacts'),
    path('api/ai-suggest/', ai_suggest_view, name='ai_suggest'),
    path('system-admin/', admin.site.urls),
]