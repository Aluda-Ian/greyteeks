from django.conf import settings
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
    PROVIDER_CHOICES = [
        ('meta', 'Meta Cloud API'),
        ('infobip', 'Infobip WhatsApp'),
    ]
    provider_type = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default='meta',
        help_text='Select the WhatsApp gateway provider'
    )
    name = models.CharField(max_length=50, default="Meta Cloud API")
    access_token = models.CharField(max_length=500)
    phone_number_id = models.CharField(max_length=100, blank=True)
    waba_id = models.CharField(max_length=100, verbose_name="WhatsApp Business Account ID", blank=True)
    infobip_base_url = models.CharField(
        max_length=255,
        blank=True,
        help_text='Infobip base URL e.g. xyz.api.infobip.com'
    )
    infobip_sender = models.CharField(
        max_length=20,
        blank=True,
        help_text='Infobip WhatsApp sender number'
    )
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"
    

class EmailProvider(models.Model):
    name = models.CharField(max_length=50, default="SMTP")
    smtp_host = models.CharField(max_length=255, help_text="SMTP host, for example smtp.gmail.com")
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=255)
    smtp_password = models.CharField(max_length=255)
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    from_email = models.EmailField(default='no-reply@greyteeks.com')
    is_active = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='email_providers',
    )

    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"

class EmailTemplate(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    provider = models.ForeignKey(EmailProvider, on_delete=models.CASCADE, related_name='templates', null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='email_templates'
    )
    name = models.CharField(max_length=100, help_text="Internal template name")
    description = models.TextField(blank=True, default='', help_text="Short template description")
    subject = models.CharField(max_length=200)
    body_text = models.TextField(help_text="Email body text or HTML")
    html_content = models.TextField(blank=True, default='')
    design_json = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        provider_name = self.provider.name if self.provider else 'No Provider'
        return f"{self.name} ({provider_name})"


class AIProviderSetting(models.Model):
    gemini_api_key = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'AI Provider Setting'
        verbose_name_plural = 'AI Provider Settings'

    def __str__(self):
        return 'AI Provider Configuration'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class WhatsAppDeliveryLog(models.Model):
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_delivery_logs'
    )
    contact = models.ForeignKey(
        'contacts_app.Contact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_delivery_logs'
    )
    provider = models.ForeignKey(
        WhatsAppProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_logs'
    )
    message_id = models.CharField(max_length=200, blank=True)
    external_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=50, default='unknown')
    raw_payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"WhatsApp log {self.status} for {self.contact or 'unknown contact'}"

class MessageTemplate(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_templates'
    )
    name = models.CharField(max_length=100)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

class WhatsAppTemplate(models.Model):
    provider = models.ForeignKey(WhatsAppProvider, on_delete=models.CASCADE, related_name='templates')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='whatsapp_templates'
    )
    name = models.CharField(max_length=100, help_text="The template name from Meta Dashboard")
    category = models.CharField(max_length=50, default="MARKETING")
    language_code = models.CharField(max_length=10, default="en_US")
    body_text = models.TextField(help_text="Copy of the template text for reference")

    def __str__(self):
        provider_name = self.provider.name if self.provider else 'No Provider'
        return f"{self.name} ({provider_name})"
