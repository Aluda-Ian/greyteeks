from django.contrib import admin
from django.urls import path, include
# Add ai_suggest_view to this line
from campaigns.views import about_view, contact_view, dashboard, create_campaign, home_view, manage_groups, register_view, ai_suggest_view, manage_users
from contacts_app.views import upload_contacts

admin.site.site_header = 'Greyteeks Admin'
admin.site.site_title = 'Greyteeks Admin Portal'
admin.site.index_title = 'Greyteeks Administration'

urlpatterns = [
    path('', home_view, name='home'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('register/', register_view, name='register'),
    path('dashboard/', dashboard, name='dashboard'),
    path('campaign/new/', create_campaign, name='create_campaign'),
    path('groups/manage/', manage_groups, name='manage_groups'),
    path('users/manage/', manage_users, name='manage_users'),
    path('about/', about_view, name='about'),
    path('contact/', contact_view, name='contact'),
    path('contacts/upload/', upload_contacts, name='upload_contacts'),
    path('api/ai-suggest/', ai_suggest_view, name='ai_suggest'),
    path('system-admin/', admin.site.urls),
]