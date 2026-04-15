import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django.utils import timezone

from .tasks import dispatch_campaign_task

logger = logging.getLogger(__name__)


def send_scheduled_campaigns():
    """Queue due scheduled campaigns for background processing."""
    from campaigns.models import Campaign

    now = timezone.now()
    due_campaigns = Campaign.objects.filter(
        status='scheduled',
        scheduled_time__lte=now,
    ).select_related('user')

    for campaign in due_campaigns:
        try:
            campaign.status = 'queued'
            campaign.failure_reason = ''
            campaign.save(update_fields=['status', 'failure_reason'])
            dispatch_campaign_task.delay(campaign.id)
            logger.info('Queued scheduled campaign %s for Celery processing.', campaign.id)
        except Exception as exc:
            logger.exception('Failed to queue scheduled campaign %s: %s', campaign.id, exc)
            campaign.status = 'failed'
            campaign.failure_reason = str(exc)
            campaign.save(update_fields=['status', 'failure_reason'])


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
