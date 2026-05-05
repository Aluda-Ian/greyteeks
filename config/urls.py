from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include, reverse_lazy
# Add ai_suggest_view to this line
from campaigns.views import about_view, activate_account, cancel_campaign, campaign_logs, campaigns_overview, contact_view, dashboard, create_campaign, delete_campaign, email_builder, email_builder_delete, email_builder_save, email_builder_test, home_view, manage_groups, register_view, reschedule_campaign, resend_campaign, save_email_design, scheduled_campaigns, ai_suggest_view, manage_users, manage_mailing, my_email_providers, manage_sms, manage_whatsapp, manage_templates, customer_create_group, pricing_view, service_view, faq_view, api_documentation_view, template_email_builder, track_email_open, unified_inbox, get_conversation_messages, send_inbox_reply

from contacts_app.views import contact_list, delete_contact, edit_contact, upload_contacts

admin.site.site_header = 'Greyteeks Admin'
admin.site.site_title = 'Greyteeks Admin Portal'
admin.site.index_title = 'Greyteeks Administration'

urlpatterns = [
    path('', home_view, name='home'),
    path('accounts/', include('accounts.urls')),
    path('sign-in/', auth_views.LoginView.as_view(template_name='home/sign-in.html'), name='sign_in'),
    path('sign-up/', register_view, name='sign_up'),
    path('reset-password/', auth_views.PasswordResetView.as_view(
        template_name='home/reset-password.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done')
    ), name='password_reset'),
    path('reset-password/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html', success_url=reverse_lazy('password_reset_complete')), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('register/', register_view, name='register'),
    path('activate/<uidb64>/<token>/', activate_account, name='activate'),
    path('dashboard/', dashboard, name='dashboard'),
    path('campaign/new/', create_campaign, name='create_campaign'),
    path('campaigns/<int:campaign_id>/edit/', create_campaign, name='edit_campaign'),
    path('campaigns/<int:campaign_id>/delete/', delete_campaign, name='delete_campaign'),
    path('campaigns/<int:campaign_id>/email-builder/', email_builder, name='campaign_email_builder'),
    path('campaigns/<int:campaign_id>/email-builder/save/', save_email_design, name='save_email_design'),
    path('campaigns/<int:campaign_id>/track-open/<int:contact_id>/', track_email_open, name='track_email_open'),
    path('campaigns/', campaigns_overview, name='campaigns_overview'),
    path('campaigns/logs/', campaign_logs, name='campaign_logs'),
    path('campaigns/<int:campaign_id>/resend/', resend_campaign, name='resend_campaign'),
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
    path('templates/email/builder/', template_email_builder, name='email_builder'),
    path('templates/email/builder/<int:template_id>/', template_email_builder, name='email_builder_edit'),
    path('templates/email/builder/save/', email_builder_save, name='email_builder_save'),
    path('templates/email/builder/delete/', email_builder_delete, name='email_builder_delete'),
    path('templates/email/builder/test/', email_builder_test, name='email_builder_test'),
    path('my/email-providers/', my_email_providers, name='my_email_providers'),
    path('about/', about_view, name='about'),
    path('contact/', contact_view, name='contact'),
    path('services/', service_view, name='services'),
    path('pricing/', pricing_view, name='pricing'),
    path('faq/', faq_view, name='faq'),
    path('docs/api/', api_documentation_view, name='api_documentation'),
    path('contacts/', contact_list, name='contact_list'),
    path('contacts/upload/', upload_contacts, name='upload_contacts'),
    path('contacts/<int:contact_id>/edit/', edit_contact, name='edit_contact'),
    path('contacts/<int:contact_id>/delete/', delete_contact, name='delete_contact'),
    path('contacts/forms/', include('contacts_app.urls')),
    path('', include('providers.urls')),
    path('inbox/', unified_inbox, name='unified_inbox'),
    path('api/inbox/conversations/<int:conversation_id>/', get_conversation_messages, name='get_conversation_messages'),
    path('api/inbox/conversations/<int:conversation_id>/reply/', send_inbox_reply, name='send_inbox_reply'),
    path('billing/', include('billing.urls')),
    path('api/campaigns/', include('campaigns.urls')),
    path('api/ai-suggest/', ai_suggest_view, name='ai_suggest'),
    path('system-admin/', admin.site.urls),
]
