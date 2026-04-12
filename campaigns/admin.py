from django.contrib import admin
from .models import Campaign

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'channel', 'status', 'scheduled_time')
    list_filter = ('channel', 'status')
    search_fields = ('title', 'message_body')