from django.contrib import admin
from .env_utils import update_env_file
from .models import EmailProvider, EmailTemplate, SMSProvider, WhatsAppProvider, WhatsAppTemplate


def _update_sms_provider_env(obj):
    update_env_file({
        'SMS_PROVIDER_NAME': obj.name,
        'SMS_API_KEY': obj.api_key,
        'SMS_USERNAME': obj.username,
        'SMS_SENDER_ID': obj.sender_id or '',
        'SMS_PROVIDER_ACTIVE': str(obj.is_active),
    })


def _update_whatsapp_provider_env(obj):
    update_env_file({
        'WHATSAPP_PROVIDER_TYPE': obj.provider_type,
        'WHATSAPP_PROVIDER_NAME': obj.name,
        'WHATSAPP_ACCESS_TOKEN': obj.access_token,
        'WHATSAPP_PHONE_NUMBER_ID': obj.phone_number_id or '',
        'WHATSAPP_WABA_ID': obj.waba_id or '',
        'WHATSAPP_INFOBIP_BASE_URL': obj.infobip_base_url or '',
        'WHATSAPP_INFOBIP_SENDER': obj.infobip_sender or '',
        'WHATSAPP_PROVIDER_ACTIVE': str(obj.is_active),
    })


def _update_email_provider_env(obj):
    update_env_file({
        'EMAIL_PROVIDER_NAME': obj.name,
        'EMAIL_SMTP_HOST': obj.smtp_host,
        'EMAIL_SMTP_PORT': str(obj.smtp_port),
        'EMAIL_SMTP_USERNAME': obj.smtp_username,
        'EMAIL_SMTP_PASSWORD': obj.smtp_password,
        'EMAIL_USE_TLS': str(obj.use_tls),
        'EMAIL_USE_SSL': str(obj.use_ssl),
        'EMAIL_FROM_ADDRESS': obj.from_email,
        'EMAIL_PROVIDER_ACTIVE': str(obj.is_active),
    })


class StaffOnlyAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

@admin.register(SMSProvider)
class SMSProviderAdmin(StaffOnlyAdmin):
    list_display = ('name', 'username', 'is_active')
    list_filter = ('is_active', 'name')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _update_sms_provider_env(obj)


@admin.register(WhatsAppProvider)
class WhatsAppProviderAdmin(StaffOnlyAdmin):
    list_display = ('phone_number_id', 'is_active')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _update_whatsapp_provider_env(obj)


class EmailTemplateInline(admin.TabularInline):
    model = EmailTemplate
    extra = 0

class WhatsAppTemplateInline(admin.TabularInline):
    model = WhatsAppTemplate
    extra = 0

@admin.register(EmailProvider)
class EmailProviderAdmin(StaffOnlyAdmin):
    list_display = ('name', 'smtp_host', 'smtp_username', 'is_active')
    list_filter = ('is_active',)
    inlines = [EmailTemplateInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _update_email_provider_env(obj)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(StaffOnlyAdmin):
    list_display = ('name', 'provider', 'subject', 'is_active')
    list_filter = ('provider', 'is_active')
    search_fields = ('name', 'subject', 'body_text')