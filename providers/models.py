from django.db import models

class SMSProvider(models.Model):
    PROVIDER_CHOICES = [
        ('africas_talking', 'Africa\'s Talking'),
        ('twilio', 'Twilio'),
        ('infobip', 'Infobip'),
    ]
    
    name = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    api_key = models.CharField(max_length=255)
    username = models.CharField(max_length=100, help_text="Required for Africa's Talking")
    sender_id = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_name_display()} - {'Active' if self.is_active else 'Inactive'}"

class WhatsAppProvider(models.Model):
    name = models.CharField(max_length=50, default="Meta Cloud API")
    access_token = models.CharField(max_length=500)
    phone_number_id = models.CharField(max_length=100)
    waba_id = models.CharField(max_length=100, verbose_name="WhatsApp Business Account ID")
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name