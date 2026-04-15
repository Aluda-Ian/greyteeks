from django.db import models
from config import settings

from providers.models import EmailProvider, SMSProvider, WhatsAppProvider, EmailTemplate, WhatsAppTemplate, MessageTemplate
from contacts_app.models import Contact, Group

class Campaign(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campaigns')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    message_body = models.TextField(blank=True, default='')
    html_content = models.TextField(blank=True, null=True)
    design_json = models.JSONField(blank=True, null=True)
    sms_template = models.ForeignKey(MessageTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    send_sms = models.BooleanField(default=False, verbose_name='SMS')
    send_whatsapp = models.BooleanField(default=False, verbose_name='WhatsApp')
    send_email = models.BooleanField(default=False, verbose_name='Email')

    target_group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    scheduled_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('queued', 'Queued'),
            ('processing', 'Processing'),
            ('scheduled', 'Scheduled'),
            ('completed', 'Completed'),
            ('sent', 'Sent'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft'
    )
    cancel_reason = models.TextField(blank=True)

    sms_server = models.ForeignKey(SMSProvider, on_delete=models.SET_NULL, null=True, blank=True)
    whatsapp_server = models.ForeignKey(WhatsAppProvider, on_delete=models.SET_NULL, null=True, blank=True)
    email_server = models.ForeignKey(EmailProvider, on_delete=models.SET_NULL, null=True, blank=True)
    whatsapp_template = models.ForeignKey(WhatsAppTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    email_template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    opens_count = models.IntegerField(default=0)
    clicks_count = models.IntegerField(default=0)
    failure_reason = models.TextField(blank=True, default='', help_text='Stores the most recent delivery failure details.')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        channels = self.enabled_channels
        label = ', '.join(channels) if channels else 'No Channel'
        return f"{self.title} ({label})"

    @property
    def enabled_channels(self):
        channels = []
        if self.send_sms:
            channels.append('SMS')
        if self.send_whatsapp:
            channels.append('WhatsApp')
        if self.send_email:
            channels.append('Email')
        return channels

    @property
    def active_channel_labels(self):
        return ', '.join(self.enabled_channels) if self.enabled_channels else 'None'


class CampaignOpenEvent(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='open_events')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='campaign_open_events')
    opened_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-opened_at']

    def __str__(self):
        return f"Open for {self.campaign_id} by {self.contact_id}"
