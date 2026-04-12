from django.db import models
from providers.models import SMSProvider, WhatsAppProvider
from contacts.models import Group 

class Campaign(models.Model):
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    title = models.CharField(max_length=200)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    message_body = models.TextField()
    
    # NEW FIELD: This connects the campaign to your Nairobi contact lists
    target_group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Scheduling & Status
    scheduled_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Linking to the specific "Server" (Provider)
    sms_server = models.ForeignKey(SMSProvider, on_delete=models.SET_NULL, null=True, blank=True)
    whatsapp_server = models.ForeignKey(WhatsAppProvider, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.channel})"