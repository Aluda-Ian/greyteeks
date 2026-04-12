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
    name = models.CharField(max_length=50, default="Meta Cloud API")
    access_token = models.CharField(max_length=500)
    phone_number_id = models.CharField(max_length=100)
    waba_id = models.CharField(max_length=100, verbose_name="WhatsApp Business Account ID")
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    

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
    provider = models.ForeignKey(EmailProvider, on_delete=models.CASCADE, related_name='templates', null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='email_templates'
    )
    name = models.CharField(max_length=100, help_text="Internal template name")
    subject = models.CharField(max_length=200)
    body_text = models.TextField(help_text="Email body text or HTML")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        provider_name = self.provider.name if self.provider else 'No Provider'
        return f"{self.name} ({provider_name})"

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
    name = models.CharField(max_length=100, help_text="The template name from Meta Dashboard")
    category = models.CharField(max_length=50, default="MARKETING")
    language_code = models.CharField(max_length=10, default="en_US")
    body_text = models.TextField(help_text="Copy of the template text for reference")

    def __str__(self):
        return f"{self.name} ({self.provider.name})"