import logging

from celery import shared_task
from django.utils import timezone

from .models import Campaign
from accounts.models import UserQuota
from providers.services import route_sms, route_whatsapp, send_custom_email

logger = logging.getLogger(__name__)


def _resolve_email_payload(campaign):
    if campaign.email_template:
        subject = campaign.email_template.subject
        html_body = campaign.email_template.html_content or ''
        fallback_body = campaign.email_template.body_text
    else:
        subject = campaign.title
        html_body = campaign.html_content or ''
        fallback_body = campaign.message_body

    body = html_body or fallback_body or ''
    is_html = bool(html_body)
    return subject, body, is_html


def _summarize_failures(failures, total_failures):
    if not failures:
        return ''

    preview = ' | '.join(failures[:10])
    if total_failures > len(failures[:10]):
        preview = f'{preview} | ...and {total_failures - len(failures[:10])} more.'
    return preview


@shared_task
def dispatch_campaign_task(campaign_id):
    campaign = Campaign.objects.select_related(
        'target_group',
        'sms_server',
        'whatsapp_server',
        'email_server',
        'sms_template',
        'whatsapp_template',
        'email_template',
        'user',
    ).filter(id=campaign_id).first()

    if not campaign:
        logger.warning('Campaign %s not found for dispatch.', campaign_id)
        return {'status': 'failed', 'reason': 'Campaign not found.'}

    if campaign.status not in ('queued', 'scheduled'):
        logger.info('Campaign %s skipped because status is %s.', campaign.id, campaign.status)
        return {'status': 'skipped', 'reason': f'Campaign is currently {campaign.status}.'}

    if campaign.scheduled_time and campaign.scheduled_time > timezone.now() and campaign.status == 'scheduled':
        logger.info('Campaign %s skipped because scheduled time has not arrived.', campaign.id)
        return {'status': 'delayed', 'reason': 'Campaign scheduled for future delivery.'}

    contacts = list(campaign.target_group.contacts.all()) if campaign.target_group else []
    if not contacts:
        campaign.status = 'failed'
        campaign.failure_reason = 'No contacts were found in the selected target group.'
        campaign.save(update_fields=['status', 'failure_reason'])
        logger.warning('Campaign %s failed because it has no contacts.', campaign.id)
        return {'status': 'failed', 'reason': campaign.failure_reason}

    campaign.status = 'processing'
    campaign.failure_reason = ''
    campaign.save(update_fields=['status', 'failure_reason'])

    sms_message = campaign.sms_template.body if campaign.sms_template else campaign.message_body
    whatsapp_message = campaign.whatsapp_template.body_text if campaign.whatsapp_template else campaign.message_body
    whatsapp_template_name = campaign.whatsapp_template.name if campaign.whatsapp_template else None
    email_subject, email_body, email_is_html = _resolve_email_payload(campaign)

    success_count = 0
    failure_count = 0
    failure_details = []

    for contact in contacts:
        contact_label = contact.email or contact.phone_number or f'contact-{contact.id}'

        if campaign.send_sms:
            try:
                if not campaign.sms_server:
                    raise ValueError('SMS provider is missing.')
                if not sms_message:
                    raise ValueError('SMS message body is empty.')
                if not contact.phone_number:
                    raise ValueError('Contact has no phone number for SMS.')

                sms_sent = route_sms(campaign.sms_server, [contact.phone_number], sms_message)
                if sms_sent:
                    success_count += 1
                else:
                    failure_count += 1
                    failure_details.append(f'SMS to {contact_label} failed.')
            except Exception as exc:
                failure_count += 1
                detail = f'SMS to {contact_label} failed: {exc}'
                failure_details.append(detail)
                logger.exception(detail)

        if campaign.send_whatsapp:
            try:
                if not campaign.whatsapp_server:
                    raise ValueError('WhatsApp provider is missing.')
                if not whatsapp_message:
                    raise ValueError('WhatsApp message body is empty.')
                if not contact.phone_number:
                    raise ValueError('Contact has no phone number for WhatsApp.')

                whatsapp_sent, whatsapp_detail = route_whatsapp(
                    campaign.whatsapp_server,
                    contact.phone_number,
                    whatsapp_message,
                    template_name=whatsapp_template_name,
                )
                if whatsapp_sent:
                    success_count += 1
                else:
                    failure_count += 1
                    failure_details.append(
                        f'WhatsApp to {contact_label} failed: {whatsapp_detail or "Unknown delivery error."}'
                    )
            except Exception as exc:
                failure_count += 1
                detail = f'WhatsApp to {contact_label} failed: {exc}'
                failure_details.append(detail)
                logger.exception(detail)

        if campaign.send_email:
            try:
                if not campaign.email_server:
                    raise ValueError('Email provider is missing.')
                if not email_body:
                    raise ValueError('Email content is empty.')
                if not contact.email:
                    raise ValueError('Contact has no email address.')

                email_sent, email_detail = send_custom_email(
                    campaign.email_server,
                    email_subject,
                    email_body,
                    [contact.email],
                    from_email=campaign.email_server.from_email,
                    html_message=email_is_html,
                )
                if email_sent:
                    success_count += 1
                else:
                    failure_count += 1
                    failure_details.append(
                        f'Email to {contact_label} failed: {email_detail or "Unknown delivery error."}'
                    )
            except Exception as exc:
                failure_count += 1
                detail = f'Email to {contact_label} failed: {exc}'
                failure_details.append(detail)
                logger.exception(detail)

    final_status = 'completed' if success_count > 0 else 'failed'
    campaign.status = final_status
    campaign.failure_reason = _summarize_failures(failure_details, failure_count)
    campaign.save(update_fields=['status', 'failure_reason'])

    if success_count > 0:
        quota, _ = UserQuota.objects.get_or_create(user=campaign.user)
        quota.units_used += success_count
        quota.save(update_fields=['units_used'])

    logger.info(
        'Campaign %s finished with status=%s, successes=%s, failures=%s.',
        campaign.id,
        final_status,
        success_count,
        failure_count,
    )
    return {
        'status': final_status,
        'campaign_id': campaign.id,
        'success_count': success_count,
        'failure_count': failure_count,
        'failure_reason': campaign.failure_reason,
    }
