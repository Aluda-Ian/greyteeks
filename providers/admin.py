from django.contrib import admin
from .models import EmailProvider, EmailTemplate, SMSProvider, WhatsAppProvider, WhatsAppTemplate

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

@admin.register(WhatsAppProvider)
class WhatsAppProviderAdmin(StaffOnlyAdmin):
    list_display = ('phone_number_id', 'is_active')

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

@admin.register(EmailTemplate)
class EmailTemplateAdmin(StaffOnlyAdmin):
    list_display = ('name', 'provider', 'subject', 'is_active')
    list_filter = ('provider', 'is_active')
    search_fields = ('name', 'subject', 'body_text')