from django.contrib import admin
from .models import EmailProvider, EmailTemplate, SMSProvider, WhatsAppProvider, WhatsAppTemplate

@admin.register(SMSProvider)
class SMSProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'username', 'is_active')
    list_filter = ('is_active', 'name')

@admin.register(WhatsAppProvider)
class WhatsAppProviderAdmin(admin.ModelAdmin):
    list_display = ('phone_number_id', 'is_active')

class EmailTemplateInline(admin.TabularInline):
    model = EmailTemplate
    extra = 0

class WhatsAppTemplateInline(admin.TabularInline):
    model = WhatsAppTemplate
    extra = 0

@admin.register(EmailProvider)
class EmailProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'host', 'username', 'is_active')
    list_filter = ('is_active',)
    inlines = [EmailTemplateInline]

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'subject', 'is_active')
    list_filter = ('provider', 'is_active')
    search_fields = ('name', 'subject', 'body_text')