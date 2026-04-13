import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_scheduled_campaigns():
    """Job that runs every minute and sends due scheduled campaigns."""
    from campaigns.models import Campaign
    from providers.services import route_sms, route_whatsapp, send_custom_email
    from accounts.models import UserQuota

    now = timezone.now()

    due_campaigns = Campaign.objects.filter(
        status='scheduled',
        scheduled_time__lte=now
    ).select_related(
        'target_group', 'sms_server', 'whatsapp_server', 'email_server', 'whatsapp_template', 'email_template'
    )

    for campaign in due_campaigns:
        logger.info(f"Processing scheduled campaign: {campaign.id} — {campaign.title}")
        try:
            contacts = campaign.target_group.contacts.all() if campaign.target_group else []
            sms_recipients = [c.phone_number for c in contacts if c.phone_number]
            email_recipients = [c.email for c in contacts if c.email]
            whatsapp_recipients = sms_recipients

            channel_success = True

            if campaign.send_sms:
                if campaign.sms_server and sms_recipients:
                    sent = route_sms(campaign.sms_server, sms_recipients, campaign.message_body)
                    channel_success = channel_success and sent
                else:
                    channel_success = False

            if campaign.send_whatsapp:
                if campaign.whatsapp_server and whatsapp_recipients:
                    outbound_text = campaign.whatsapp_template.body_text if campaign.whatsapp_template else campaign.message_body
                    for number in whatsapp_recipients:
                        sent = route_whatsapp(campaign.whatsapp_server, number, outbound_text)
                        if not sent:
                            channel_success = False
                            break
                else:
                    channel_success = False

            if campaign.send_email:
                if campaign.email_server and email_recipients:
                    subject = campaign.email_template.subject if campaign.email_template else campaign.title
                    body = campaign.email_template.body_text if campaign.email_template else campaign.message_body
                    sent = send_custom_email(
                        campaign.email_server,
                        subject,
                        body,
                        email_recipients,
                        from_email=campaign.email_server.from_email
                    )
                    channel_success = channel_success and sent
                else:
                    channel_success = False

            campaign.status = 'sent' if channel_success else 'failed'
            campaign.save()

            if channel_success:
                unit_count = 0
                if campaign.send_sms:
                    unit_count += len(sms_recipients)
                if campaign.send_whatsapp:
                    unit_count += len(whatsapp_recipients)
                if campaign.send_email:
                    unit_count += len(email_recipients)

                if unit_count:
                    quota, _ = UserQuota.objects.get_or_create(user=campaign.user)
                    quota.units_used += unit_count
                    quota.save()

            logger.info(f"Campaign {campaign.id} completed with status: {campaign.status}")

        except Exception as e:
            logger.error(f"Error processing campaign {campaign.id}: {e}")
            campaign.status = 'failed'
            campaign.save()


def delete_old_job_executions(max_age=604_800):
    """Delete APScheduler job execution entries older than max_age seconds."""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), 'default')

    scheduler.add_job(
        send_scheduled_campaigns,
        trigger=IntervalTrigger(minutes=1),
        id='send_scheduled_campaigns',
        max_instances=1,
        replace_existing=True,
    )
    logger.info('Added job: send_scheduled_campaigns (every 1 minute)')

    scheduler.add_job(
        delete_old_job_executions,
        trigger=IntervalTrigger(weeks=1),
        id='delete_old_job_executions',
        max_instances=1,
        replace_existing=True,
    )
    logger.info('Added job: delete_old_job_executions (weekly)')

    try:
        logger.info('Starting APScheduler...')
        scheduler.start()
    except KeyboardInterrupt:
        logger.info('Stopping APScheduler...')
        scheduler.shutdown()
        logger.info('APScheduler shut down successfully.')
