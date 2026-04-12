from django import forms
from .models import Campaign

class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['title', 'channel', 'message_body', 'target_group', 'sms_server', 'whatsapp_server', 'whatsapp_template', 'email_server', 'email_template']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Campaign Name'}),
            'channel': forms.Select(attrs={'class': 'form-select'}),
            'message_body': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'id': 'messageBody'}),
            'sms_server': forms.Select(attrs={'class': 'form-select'}),
            'whatsapp_server': forms.Select(attrs={'class': 'form-select'}),
            'whatsapp_template': forms.Select(attrs={'class': 'form-select'}),
            'email_server': forms.Select(attrs={'class': 'form-select'}),
            'email_template': forms.Select(attrs={'class': 'form-select'}),
            'target_group': forms.Select(attrs={'class': 'form-select'}),
        }