from django import forms
from django.db.models import Q
from .models import Campaign
from providers.models import EmailProvider, EmailTemplate, SMSProvider, WhatsAppProvider, WhatsAppTemplate

class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = [
            'title',
            'target_group',
            'send_sms',
            'sms_server',
            'send_whatsapp',
            'whatsapp_server',
            'whatsapp_template',
            'send_email',
            'email_server',
            'email_template',
            'message_body',
        ]
        labels = {
            'send_sms': 'SMS Channel',
            'send_whatsapp': 'WhatsApp Channel',
            'send_email': 'Email Channel',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Campaign Name'}),
            'message_body': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'id': 'messageBody'}),
            'sms_server': forms.Select(attrs={'class': 'form-select'}),
            'whatsapp_server': forms.Select(attrs={'class': 'form-select'}),
            'whatsapp_template': forms.Select(attrs={'class': 'form-select'}),
            'email_server': forms.Select(attrs={'class': 'form-select'}),
            'email_template': forms.Select(attrs={'class': 'form-select'}),
            'target_group': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        email_queryset = EmailProvider.objects.filter(is_active=True)
        if user is not None:
            email_queryset = EmailProvider.objects.filter(
                Q(owner=user) | Q(owner__isnull=True, is_active=True)
            )
        self.fields['email_server'].queryset = email_queryset
        self.fields['email_template'].queryset = EmailTemplate.objects.filter(is_active=True)
        self.fields['sms_server'].queryset = SMSProvider.objects.filter(is_active=True)
        self.fields['whatsapp_server'].queryset = WhatsAppProvider.objects.filter(is_active=True)
        self.fields['whatsapp_template'].queryset = WhatsAppTemplate.objects.all()
        if 'email_server' in self.data:
            try:
                provider_id = int(self.data.get('email_server'))
                self.fields['email_template'].queryset = EmailTemplate.objects.filter(provider_id=provider_id, is_active=True)
            except (TypeError, ValueError):
                pass
