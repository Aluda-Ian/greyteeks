from celery import shared_task
from django.utils import timezone

from .models import Campaign
from accounts.models import UserQuota
from providers.services import route_sms, route_whatsapp, send_custom_email


@shared_task(bind=True)
def dispatch_campaign_task(self, campaign_id):
    campaign = Campaign.objects.select_related(
        'target_group',
        'sms_server',
        'whatsapp_server',
        'email_server',
        'sms_template',
        'whatsapp_template',
        'email_template',
        'user'
    ).filter(id=campaign_id).first()

    if not campaign:
        return {'status': 'failed', 'reason': 'Campaign not found.'}

    if campaign.status not in ('draft', 'scheduled'):
        return {'status': 'skipped', 'reason': 'Campaign already processed or cancelled.'}

    if campaign.scheduled_time and campaign.scheduled_time > timezone.now():
        return {'status': 'delayed', 'reason': 'Campaign scheduled for future delivery.'}

    contacts = campaign.target_group.contacts.all() if campaign.target_group else []
    sms_recipients = [c.phone_number for c in contacts if c.phone_number]
    whatsapp_recipients = sms_recipients
    email_recipients = [c.email for c in contacts if c.email]

    channel_success = True
    unit_count = 0
    failure_reason = ''

    if campaign.send_sms:
        if not campaign.sms_server or not campaign.sms_template or not sms_recipients:
            channel_success = False
            failure_reason = 'SMS channel has missing provider, template, or recipients.'
        else:
            sms_sent = route_sms(campaign.sms_server, sms_recipients, campaign.sms_template.body)
            if not sms_sent:
                channel_success = False
                failure_reason = 'SMS delivery failed.'
            unit_count += len(sms_recipients)

    if campaign.send_whatsapp:
        if not campaign.whatsapp_server or not whatsapp_recipients:
            channel_success = False
            failure_reason = failure_reason or 'WhatsApp channel has missing provider or recipients.'
        else:
            outbound_text = campaign.whatsapp_template.body_text if campaign.whatsapp_template else campaign.message_body
            if not outbound_text:
                channel_success = False
                failure_reason = failure_reason or 'WhatsApp channel requires a message body or template.'
            else:
                for number in whatsapp_recipients:
                    whatsapp_sent, whatsapp_detail = route_whatsapp(
                        campaign.whatsapp_server,
                        number,
                        outbound_text,
                        template_name=(campaign.whatsapp_template.name if campaign.whatsapp_template else None)
                    )
                    if not whatsapp_sent:
                        channel_success = False
                        failure_reason = failure_reason or whatsapp_detail or 'WhatsApp delivery failed.'
                        break
                unit_count += len(whatsapp_recipients)

    if campaign.send_email:
        if not campaign.email_server or not email_recipients:
            channel_success = False
            failure_reason = failure_reason or 'Email channel has missing provider or recipients.'
        else:
            outbound_subject = campaign.email_template.subject if campaign.email_template else campaign.title
            outbound_body = campaign.email_template.body_text if campaign.email_template else campaign.message_body
            email_sent, email_detail = send_custom_email(
                campaign.email_server,
                outbound_subject,
                outbound_body,
                email_recipients,
                from_email=campaign.email_server.from_email
            )
            if not email_sent:
                channel_success = False
                failure_reason = failure_reason or email_detail or 'Email delivery failed.'
            unit_count += len(email_recipients)

    campaign.status = 'sent' if channel_success else 'failed'
    campaign.failure_reason = '' if channel_success else failure_reason
    campaign.save()

    return {
        'status': 'sent' if channel_success else 'failed',
        'units_processed': unit_count,
        'failure_reason': failure_reason,
    }
