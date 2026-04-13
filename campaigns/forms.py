from django import forms
from django.db.models import Q
from .models import Campaign
from contacts_app.models import Group
from providers.models import EmailProvider, EmailTemplate, MessageTemplate, SMSProvider, WhatsAppProvider, WhatsAppTemplate

class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = [
            'title',
            'target_group',
            'description',
            'send_sms',
            'sms_server',
            'sms_template',
            'send_whatsapp',
            'whatsapp_server',
            'whatsapp_template',
            'send_email',
            'email_server',
            'email_template',
        ]
        labels = {
            'send_sms': 'SMS Channel',
            'send_whatsapp': 'WhatsApp Channel',
            'send_email': 'Email Channel',
            'sms_template': 'SMS Template',
            'whatsapp_template': 'WhatsApp Template',
            'email_template': 'Email Template',
            'description': 'Campaign Description',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Campaign Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'id': 'campaignDescription', 'placeholder': 'Describe the campaign for internal reference.'}),
            'sms_server': forms.Select(attrs={'class': 'form-select'}),
            'sms_template': forms.Select(attrs={'class': 'form-select'}),
            'whatsapp_server': forms.Select(attrs={'class': 'form-select'}),
            'whatsapp_template': forms.Select(attrs={'class': 'form-select'}),
            'email_server': forms.Select(attrs={'class': 'form-select'}),
            'email_template': forms.Select(attrs={'class': 'form-select'}),
            'target_group': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['target_group'].queryset = Group.objects.filter(user=self.user)

        email_queryset = EmailProvider.objects.filter(is_active=True)
        if self.user is not None:
            email_queryset = EmailProvider.objects.filter(
                Q(owner=self.user) | Q(owner__isnull=True, is_active=True)
            )
        self.fields['email_server'].queryset = email_queryset
        self.fields['email_template'].queryset = EmailTemplate.objects.filter(
            Q(owner=self.user) | Q(owner__isnull=True, is_active=True)
        )
        self.fields['sms_server'].queryset = SMSProvider.objects.filter(is_active=True)
        self.fields['whatsapp_server'].queryset = WhatsAppProvider.objects.filter(is_active=True)
        self.fields['whatsapp_template'].queryset = WhatsAppTemplate.objects.filter(
            Q(owner=self.user) | Q(owner__isnull=True)
        )
        if self.user is not None:
            self.fields['sms_template'].queryset = MessageTemplate.objects.filter(owner=self.user)
        if 'email_server' in self.data:
            try:
                provider_id = int(self.data.get('email_server'))
                self.fields['email_template'].queryset = (
                    EmailTemplate.objects.filter(
                        Q(owner=self.user) |
                        Q(owner__isnull=True, is_active=True, provider_id=provider_id)
                    )
                )
            except (TypeError, ValueError):
                pass
        self.order_fields([
            'title',
            'target_group',
            'description',
            'send_sms',
            'sms_server',
            'sms_template',
            'send_whatsapp',
            'whatsapp_server',
            'whatsapp_template',
            'send_email',
            'email_server',
            'email_template',
        ])
