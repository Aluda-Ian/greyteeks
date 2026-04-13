from django.contrib import admin
from django.urls import path, include
# Add ai_suggest_view to this line
from campaigns.views import about_view, cancel_campaign, contact_view, dashboard, create_campaign, email_builder, email_builder_delete, email_builder_save, home_view, manage_groups, register_view, reschedule_campaign, scheduled_campaigns, ai_suggest_view, manage_users, manage_mailing, my_email_providers, manage_sms, manage_whatsapp, manage_templates, customer_create_group
from contacts_app.views import contact_list, delete_contact, edit_contact, upload_contacts

admin.site.site_header = 'Greyteeks Admin'
admin.site.site_title = 'Greyteeks Admin Portal'
admin.site.index_title = 'Greyteeks Administration'

urlpatterns = [
    path('', home_view, name='home'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('register/', register_view, name='register'),
    path('dashboard/', dashboard, name='dashboard'),
    path('campaign/new/', create_campaign, name='create_campaign'),
    path('campaigns/scheduled/', scheduled_campaigns, name='scheduled_campaigns'),
    path('campaigns/<int:campaign_id>/cancel/', cancel_campaign, name='cancel_campaign'),
    path('campaigns/<int:campaign_id>/reschedule/', reschedule_campaign, name='reschedule_campaign'),
    path('groups/manage/', manage_groups, name='manage_groups'),
    path('users/manage/', manage_users, name='manage_users'),
    path('mailing/manage/', manage_mailing, name='manage_mailing'),
    path('sms/manage/', manage_sms, name='manage_sms'),
    path('whatsapp/manage/', manage_whatsapp, name='manage_whatsapp'),
    path('my/groups/', customer_create_group, name='customer_create_group'),
    path('templates/manage/', manage_templates, name='manage_templates'),
    path('templates/email/builder/', email_builder, name='email_builder'),
    path('templates/email/builder/<int:template_id>/', email_builder, name='email_builder_edit'),
    path('templates/email/builder/save/', email_builder_save, name='email_builder_save'),
    path('templates/email/builder/delete/', email_builder_delete, name='email_builder_delete'),
    path('my/email-providers/', my_email_providers, name='my_email_providers'),
    path('about/', about_view, name='about'),
    path('contact/', contact_view, name='contact'),
    path('contacts/', contact_list, name='contact_list'),
    path('contacts/upload/', upload_contacts, name='upload_contacts'),
    path('contacts/<int:contact_id>/edit/', edit_contact, name='edit_contact'),
    path('contacts/<int:contact_id>/delete/', delete_contact, name='delete_contact'),
    path('billing/', include('billing.urls')),
    path('api/ai-suggest/', ai_suggest_view, name='ai_suggest'),
    path('system-admin/', admin.site.urls),
]