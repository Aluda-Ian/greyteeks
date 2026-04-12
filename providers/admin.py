from django.contrib import admin
from .models import SMSProvider, WhatsAppProvider

@admin.register(SMSProvider)
class SMSProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'username', 'is_active')
    list_filter = ('is_active', 'name')

@admin.register(WhatsAppProvider)
class WhatsAppProviderAdmin(admin.ModelAdmin):
    list_display = ('phone_number_id', 'is_active')