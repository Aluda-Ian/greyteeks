from django.contrib import admin
from .models import Campaign

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'active_channel_labels', 'target_group', 'status', 'scheduled_time')
    list_filter = ('status', 'target_group')
    search_fields = ('title', 'message_body', 'user__username')
    raw_id_fields = ('target_group', 'sms_server', 'whatsapp_server', 'email_server', 'whatsapp_template', 'email_template')