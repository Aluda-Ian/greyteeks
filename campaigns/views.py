from django.shortcuts import get_object_or_404, redirect, render

import json

from django.http import HttpResponse, JsonResponse

from django.contrib import messages

from django.core.exceptions import PermissionDenied

from django.db import IntegrityError, models, transaction

from django.db.models import F, Sum

from django.conf import settings as django_settings

from django.utils import timezone

from django.utils.dateparse import parse_datetime

from django.contrib.auth import login

from django.contrib.auth.models import User

from django.contrib.auth.decorators import login_required

from django.contrib.auth.tokens import default_token_generator

from django.core.mail import send_mail

from django.urls import reverse

from django.utils.encoding import force_bytes, force_str

from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from contacts_app.models import Contact, Group, Conversation, Message

from accounts.models import UserQuota

from billing.models import PaymentTransaction

from .models import Campaign, CampaignOpenEvent

from .forms import CampaignForm
from .tasks import dispatch_campaign_task

from .utils import get_ai_campaign_suggestion

from providers.models import EmailProvider, EmailTemplate, MessageTemplate, SMSProvider, WhatsAppProvider, WhatsAppTemplate

from providers.services import route_sms, route_whatsapp, send_custom_email, test_whatsapp_meta_connection, test_whatsapp_infobip_connection, send_whatsapp_meta_message



def home_view(request):

    """Public landing page. Redirects authenticated users to their dashboard."""

    if request.user.is_authenticated:

        return redirect('dashboard')

    return render(request, 'home/home.html')



@login_required

def dashboard(request):

    """

    Role-based Dashboard:

    - Admins (staff) see global system-wide statistics.

    - Customers see only their personal marketing data.

    """

    delivered_statuses = ['sent', 'completed']

    if request.user.is_staff:

        # Admin View: Aggregated system data

        total_campaigns = Campaign.objects.count()

        total_contacts = Contact.objects.count()

        total_groups = Group.objects.count()

        total_users = User.objects.count()

        total_scheduled = Campaign.objects.filter(status='scheduled').count()

        recent_campaigns = Campaign.objects.order_by('-created_at')[:10]

        total_sms_sent = Campaign.objects.filter(send_sms=True, status__in=delivered_statuses).count()

        total_whatsapp_sent = Campaign.objects.filter(send_whatsapp=True, status__in=delivered_statuses).count()

        total_email_sent = Campaign.objects.filter(send_email=True, status__in=delivered_statuses).count()

        transaction_qs = PaymentTransaction.objects.filter(status='success')

        user_quota = None

        quota_progress = None

    else:

        # Customer View: Isolated personal data

        user_campaigns = Campaign.objects.filter(user=request.user)

        total_campaigns = user_campaigns.count()

        total_groups = Group.objects.filter(user=request.user).count()

        total_contacts = Contact.objects.filter(group__user=request.user).count()

        total_scheduled = user_campaigns.filter(status='scheduled').count()

        recent_campaigns = user_campaigns.order_by('-created_at')[:5]

        total_sms_sent = user_campaigns.filter(send_sms=True, status__in=delivered_statuses).count()

        total_whatsapp_sent = user_campaigns.filter(send_whatsapp=True, status__in=delivered_statuses).count()

        total_email_sent = user_campaigns.filter(send_email=True, status__in=delivered_statuses).count()

        transaction_qs = PaymentTransaction.objects.filter(user=request.user, status='success')

        user_quota = getattr(request.user, 'quota', None)

        quota_progress = None

        if user_quota and user_quota.max_units:

            quota_progress = int((user_quota.units_used / user_quota.max_units) * 100)



    total_successful_payments = transaction_qs.count()

    total_revenue_kes = transaction_qs.filter(currency='KES').aggregate(total=Sum('amount'))['total'] or 0

    total_revenue_usd = transaction_qs.filter(currency='USD').aggregate(total=Sum('amount'))['total'] or 0



    context = {

        'total_campaigns': total_campaigns,

        'total_contacts': total_contacts,

        'total_groups': total_groups,

        'total_users': total_users if request.user.is_staff else None,

        'total_scheduled': total_scheduled,

        'recent_campaigns': recent_campaigns,

        'total_sms_sent': total_sms_sent,

        'total_whatsapp_sent': total_whatsapp_sent,

        'total_email_sent': total_email_sent,

        'total_successful_payments': total_successful_payments,

        'total_revenue_kes': total_revenue_kes,

        'total_revenue_usd': total_revenue_usd,

        'user_quota': user_quota,

        'quota_progress': quota_progress,

        'has_groups': Group.objects.filter(user=request.user).exists() if not request.user.is_staff else None,

        'has_contacts': Contact.objects.filter(group__user=request.user).exists() if not request.user.is_staff else None,

    }

    return render(request, 'campaigns/dashboard.html', context)



@login_required

def campaigns_overview(request):

    if request.user.is_staff:

        campaigns = Campaign.objects.order_by('-created_at').select_related('user', 'target_group')

    else:

        campaigns = Campaign.objects.filter(user=request.user).order_by('-created_at').select_related('target_group')



    return render(request, 'campaigns/campaigns_overview.html', {

        'campaigns': campaigns,

    })



@login_required

def campaign_logs(request):

    if not request.user.is_staff:

        raise PermissionDenied



    failed_campaigns = Campaign.objects.filter(status='failed').order_by('-created_at').select_related('user', 'target_group')

    return render(request, 'campaigns/campaign_logs.html', {

        'failed_campaigns': failed_campaigns,

    })



@login_required
def unified_inbox(request):
    conversations = Conversation.objects.filter(user=request.user).select_related('contact').order_by('-last_updated')
    conversation_list = []
    for conversation in conversations:
        latest_message = conversation.messages.order_by('-timestamp').first()
        conversation_list.append({
            'id': conversation.id,
            'contact_name': conversation.contact.name or conversation.contact.phone_number,
            'phone_number': conversation.contact.phone_number,
            'last_message': latest_message.content[:80] if latest_message else 'No messages yet.',
            'last_updated': conversation.last_updated.isoformat(),
            'unread_count': conversation.messages.filter(direction='inbound', is_read=False).count(),
        })

    return render(request, 'campaigns/inbox.html', {
        'conversations': conversation_list,
        'active_conversation_id': conversation_list[0]['id'] if conversation_list else None,
    })


@login_required
def get_conversation_messages(request, conversation_id):
    conversation = Conversation.objects.filter(id=conversation_id, user=request.user).select_related('contact').first()
    if not conversation:
        return JsonResponse({'error': 'Conversation not found.'}, status=404)

    messages = list(conversation.messages.order_by('timestamp').all())
    conversation.messages.filter(direction='inbound', is_read=False).update(is_read=True)

    formatted_messages = []
    for message in messages:
        formatted_messages.append({
            'id': message.id,
            'direction': message.direction,
            'channel': message.channel,
            'content': message.content,
            'timestamp': message.timestamp.astimezone(timezone.get_current_timezone()).strftime('%b %d, %I:%M %p'),
            'is_read': message.is_read,
        })

    return JsonResponse({
        'conversation': {
            'id': conversation.id,
            'contact_name': conversation.contact.name or conversation.contact.phone_number,
            'phone_number': conversation.contact.phone_number,
        },
        'messages': formatted_messages,
    })


@login_required
def send_inbox_reply(request, conversation_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required.'}, status=405)

    conversation = Conversation.objects.filter(id=conversation_id, user=request.user).select_related('contact').first()
    if not conversation:
        return JsonResponse({'error': 'Conversation not found.'}, status=404)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    message_text = payload.get('message', '').strip()
    if not message_text:
        return JsonResponse({'error': 'Reply text is required.'}, status=400)

    provider = WhatsAppProvider.objects.filter(is_active=True).first()
    if not provider:
        return JsonResponse({'error': 'No active WhatsApp provider available.'}, status=400)

    reply = Message.objects.create(
        conversation=conversation,
        direction='outbound',
        channel='whatsapp',
        content=message_text,
        is_read=True,
    )

    success, dispatch_message = send_whatsapp_meta_message(provider, conversation.contact.phone_number, message_text)
    if not success:
        return JsonResponse({'error': dispatch_message}, status=500)

    conversation.save(update_fields=['last_updated'])

    return JsonResponse({
        'success': True,
        'message': 'Reply sent successfully.',
        'sent_message': {
            'id': reply.id,
            'direction': reply.direction,
            'channel': reply.channel,
            'content': reply.content,
            'timestamp': reply.timestamp.astimezone(timezone.get_current_timezone()).strftime('%b %d, %I:%M %p'),
            'is_read': reply.is_read,
        },
    })


def _attempt_campaign_send(request, campaign):
    if not campaign.target_group:
        return False, 'Please assign a target group before resending this campaign.'

    contacts = campaign.target_group.contacts.all()
    sms_recipients = [c.phone_number for c in contacts if c.phone_number]
    whatsapp_recipients = sms_recipients
    email_recipients = [c.email for c in contacts if c.email]

    if campaign.send_sms:
        if not campaign.sms_server:
            campaign.failure_reason = 'No SMS provider selected. Please contact support to activate an SMS provider.'
            campaign.status = 'failed'
            campaign.save()
            return False, campaign.failure_reason
        if not campaign.sms_template:
            campaign.failure_reason = 'SMS sending requires a configured SMS template.'
            campaign.status = 'failed'
            campaign.save()
            return False, campaign.failure_reason
        if not sms_recipients:
            campaign.failure_reason = 'No valid SMS recipients are available for this campaign.'
            campaign.status = 'failed'
            campaign.save()
            return False, campaign.failure_reason

    if campaign.send_whatsapp:
        if not campaign.whatsapp_server:
            campaign.failure_reason = 'No WhatsApp provider selected. Please contact support to activate a WhatsApp provider.'
            campaign.status = 'failed'
            campaign.save()
            return False, campaign.failure_reason
        if not whatsapp_recipients:
            campaign.failure_reason = 'No valid WhatsApp recipients are available for this campaign.'
            campaign.status = 'failed'
            campaign.save()
            return False, campaign.failure_reason

    if campaign.send_email:
        if not campaign.email_server:
            campaign.failure_reason = 'No email provider selected. Please configure an SMTP provider first.'
            campaign.status = 'failed'
            campaign.save()
            return False, campaign.failure_reason
        if not campaign.email_server.is_active:
            campaign.failure_reason = 'The selected email provider is inactive. Please choose an active provider.'
            campaign.status = 'failed'
            campaign.save()
            return False, campaign.failure_reason
        if not email_recipients:
            campaign.failure_reason = 'No valid email recipients are available for this campaign.'
            campaign.status = 'failed'
            campaign.save()
            return False, campaign.failure_reason

    if campaign.send_sms and campaign.sms_template:
        campaign.message_body = campaign.sms_template.body

    channel_success = True
    unit_count = 0
    failure_reason = ''

    if campaign.send_sms:
        sms_sent = route_sms(campaign.sms_server, sms_recipients, campaign.message_body)
        if not sms_sent:
            channel_success = False
            if not failure_reason:
                failure_reason = 'SMS send failed. Check SMS provider settings.'
        unit_count += len(sms_recipients)

    if campaign.send_whatsapp:
        outbound_text = campaign.whatsapp_template.body_text if campaign.whatsapp_template else campaign.message_body
        if not outbound_text:
            campaign.failure_reason = 'WhatsApp channel requires a valid message body or template.'
            campaign.status = 'failed'
            campaign.save()
            return False, 'WhatsApp channel requires a valid message body or template.'
        for number in whatsapp_recipients:
            whatsapp_sent, whatsapp_detail = route_whatsapp(campaign.whatsapp_server, number, outbound_text)
            if not whatsapp_sent:
                channel_success = False
                if not failure_reason:
                    failure_reason = whatsapp_detail or 'WhatsApp send failed.'
                break
        unit_count += len(whatsapp_recipients)

    if campaign.send_email:
        outbound_subject = campaign.email_template.subject if campaign.email_template else campaign.title
        outbound_body = (
            campaign.email_template.html_content
            if campaign.email_template and campaign.email_template.html_content
            else campaign.email_template.body_text
            if campaign.email_template
            else campaign.html_content or campaign.message_body
        )
        email_sent, email_detail = send_custom_email(
            campaign.email_server,
            outbound_subject,
            outbound_body,
            email_recipients,
            from_email=campaign.email_server.from_email
        )
        if not email_sent:
            channel_success = False
            if not failure_reason:
                failure_reason = email_detail or 'Email send failed. Check SMTP provider settings.'
        unit_count += len(email_recipients)

    campaign.status = 'sent' if channel_success else 'failed'
    campaign.failure_reason = '' if channel_success else (failure_reason or 'One or more channels failed to send.')
    campaign.save()

    if channel_success:
        quota = getattr(request.user, 'quota', None)
        if quota is None:
            quota = UserQuota.objects.create(user=request.user)
        quota.units_used += unit_count
        quota.save()
        return True, 'Campaign resent successfully.'

    return False, 'Resend failed. Review provider settings and try again.'


@login_required

def resend_campaign(request, campaign_id):
    if request.method != 'POST':
        return redirect('campaigns_overview')

    if request.user.is_staff:
        campaign = Campaign.objects.filter(id=campaign_id, status='failed').first()
    else:
        campaign = Campaign.objects.filter(id=campaign_id, user=request.user, status='failed').first()

    if not campaign:
        messages.error(request, 'Failed campaign not found or you do not have permission to resend it.')
        return redirect('campaigns_overview')

    success, message = _attempt_campaign_send(request, campaign)
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('campaigns_overview')


def delete_campaign(request, campaign_id):

    if request.method != 'POST':

        return redirect('campaigns_overview')



    if request.user.is_staff:

        campaign = Campaign.objects.filter(id=campaign_id).first()

    else:

        campaign = Campaign.objects.filter(id=campaign_id, user=request.user).first()



    if not campaign:

        messages.error(request, 'Campaign not found.')

        return redirect('campaigns_overview')



    if campaign.status != 'draft':

        messages.error(request, 'Only draft campaigns can be deleted.')

        return redirect('campaigns_overview')



    campaign.delete()

    messages.success(request, 'Draft campaign deleted successfully.')

    return redirect('campaigns_overview')



def about_view(request):

    return render(request, 'home/about.html')





def contact_view(request):

    if request.method == 'POST':

        name = request.POST.get('name', '').strip()

        email = request.POST.get('email', '').strip()

        subject = request.POST.get('subject', '').strip()

        message = request.POST.get('message', '').strip()



        if not name or not email or not subject or not message:

            messages.error(request, 'Please complete all required fields.')

        else:

            messages.success(request, f'Thanks {name}, we will respond to {email} shortly.')

            return redirect('contact')



    return render(request, 'home/contact_us.html')



@login_required

def manage_users(request):

    if not request.user.is_staff:

        raise PermissionDenied



    if request.method == 'POST':

        user_id = request.POST.get('user_id')

        action = request.POST.get('action')

        target_user = User.objects.filter(id=user_id).exclude(id=request.user.id).first()



        if target_user and action == 'toggle_active':

            target_user.is_active = not target_user.is_active

            target_user.save()

            state = 'activated' if target_user.is_active else 'deactivated'

            messages.success(request, f"User {target_user.username} has been {state}.")



        return redirect('manage_users')



    users = User.objects.order_by('-date_joined')

    return render(request, 'campaigns/manage_users.html', {'users': users})



@login_required

def manage_groups(request):

    if not request.user.is_staff:

        raise PermissionDenied



    if request.method == 'POST':

        action = request.POST.get('action')

        if action == 'create_group':

            name = request.POST.get('name', '').strip()

            description = request.POST.get('description', '').strip()

            user_id = request.POST.get('user_id')

            owner = User.objects.filter(id=user_id).first()



            if not name or not owner:

                messages.error(request, 'Please provide a group name and an owner.')

            else:

                Group.objects.create(name=name, description=description, user=owner)

                messages.success(request, f'Group "{name}" has been created for {owner.username}.')



        elif action == 'delete_group':

            group_id = request.POST.get('group_id')

            group = Group.objects.filter(id=group_id).first()

            if group:

                group.delete()

                messages.success(request, f'Group "{group.name}" has been deleted.')



        return redirect('manage_groups')



    groups = Group.objects.select_related('user').order_by('-created_at')

    users = User.objects.order_by('username')

    return render(request, 'campaigns/manage_groups.html', {'groups': groups, 'users': users})



@login_required

def manage_mailing(request):

    if not request.user.is_staff:

        raise PermissionDenied



    if request.method == 'POST':

        action = request.POST.get('action')



        if action == 'create_provider':

            name = request.POST.get('name', '').strip()

            smtp_host = request.POST.get('smtp_host', '').strip()

            smtp_port = request.POST.get('smtp_port', '').strip()

            smtp_username = request.POST.get('smtp_username', '').strip()

            smtp_password = request.POST.get('smtp_password', '').strip()

            use_tls = request.POST.get('use_tls') == 'on'

            use_ssl = request.POST.get('use_ssl') == 'on'

            from_email = request.POST.get('from_email', '').strip()



            if not (name and smtp_host and smtp_port and smtp_username and smtp_password and from_email):

                messages.error(request, 'Please complete all required SMTP fields.')

            else:

                try:

                    EmailProvider.objects.create(

                        name=name,

                        smtp_host=smtp_host,

                        smtp_port=int(smtp_port),

                        smtp_username=smtp_username,

                        smtp_password=smtp_password,

                        use_tls=use_tls,

                        use_ssl=use_ssl,

                        from_email=from_email,

                        is_active=False,

                    )

                    messages.success(request, f'Email provider "{name}" created successfully.')

                except ValueError:

                    messages.error(request, 'SMTP port must be a valid number.')



        elif action == 'toggle_provider':

            provider_id = request.POST.get('provider_id')

            provider = EmailProvider.objects.filter(id=provider_id).first()

            if provider:

                provider.is_active = not provider.is_active

                provider.save()

                state = 'activated' if provider.is_active else 'deactivated'

                messages.success(request, f'Provider "{provider.name}" has been {state}.')



        elif action == 'delete_provider':

            provider_id = request.POST.get('provider_id')

            provider = EmailProvider.objects.filter(id=provider_id).first()

            if provider:

                provider.delete()

                messages.success(request, f'Provider "{provider.name}" has been deleted.')



        return redirect('manage_mailing')



    providers = EmailProvider.objects.order_by('-id')

    return render(request, 'campaigns/manage_mailing.html', {'providers': providers})



@login_required

def manage_templates(request):

    if request.method == 'POST':

        action = request.POST.get('action')



        if action == 'create_email_template':

            name = request.POST.get('name', '').strip()

            subject = request.POST.get('subject', '').strip()

            body_text = request.POST.get('body_text', '').strip()

            provider_id = request.POST.get('provider_id') if request.user.is_staff else None

            provider = None

            if provider_id:

                provider = EmailProvider.objects.filter(id=provider_id, is_active=True).first()



            if not (name and body_text):

                messages.error(request, 'Please provide a template name and body text.')

            else:

                EmailTemplate.objects.create(

                    provider=provider,

                    owner=None if request.user.is_staff else request.user,

                    name=name,

                    subject=subject,

                    body_text=body_text,

                    is_active=True,

                )

                messages.success(request, f'Email template "{name}" created successfully.')



        elif action == 'delete_email_template':

            template_id = request.POST.get('template_id')

            email_template = EmailTemplate.objects.filter(id=template_id).first()

            if email_template and (email_template.owner == request.user or request.user.is_staff):

                email_template.delete()

                messages.success(request, 'Email template deleted successfully.')

            else:

                messages.error(request, 'You do not have permission to delete this email template.')



        elif action == 'create_whatsapp_template':

            provider_id = request.POST.get('provider_id')

            name = request.POST.get('name', '').strip()

            category = request.POST.get('category', 'MARKETING').strip() or 'MARKETING'

            language_code = request.POST.get('language_code', 'en_US').strip() or 'en_US'

            body_text = request.POST.get('body_text', '').strip()

            provider = WhatsAppProvider.objects.filter(id=provider_id, is_active=True).first()



            if not (provider and name and body_text):

                messages.error(request, 'Please select a provider and provide a name and body for the WhatsApp template.')

            else:

                WhatsAppTemplate.objects.create(

                    provider=provider,

                    owner=request.user,

                    name=name,

                    category=category,

                    language_code=language_code,

                    body_text=body_text,

                )

                messages.success(request, f'WhatsApp template "{name}" created successfully.')



        elif action == 'delete_whatsapp_template':

            template_id = request.POST.get('template_id')

            whatsapp_template = WhatsAppTemplate.objects.filter(id=template_id).first()

            if whatsapp_template:

                whatsapp_template.delete()

                messages.success(request, 'WhatsApp template deleted successfully.')



        elif action == 'create_message_template':

            name = request.POST.get('name', '').strip()

            body = request.POST.get('body', '').strip()

            if not (name and body):

                messages.error(request, 'Please provide a message template name and body.')

            else:

                MessageTemplate.objects.create(

                    owner=request.user,

                    name=name,

                    body=body,

                )

                messages.success(request, f'Message template "{name}" created successfully.')



        elif action == 'delete_message_template':

            template_id = request.POST.get('template_id')

            message_template = MessageTemplate.objects.filter(id=template_id).first()

            if message_template and (message_template.owner == request.user or request.user.is_staff):

                message_template.delete()

                messages.success(request, 'Message template deleted successfully.')

            else:

                messages.error(request, 'You do not have permission to delete this message template.')



        return redirect('manage_templates')



    email_templates = EmailTemplate.objects.filter(

        models.Q(owner=request.user) | models.Q(owner=None)

    ).order_by('-created_at')

    whatsapp_templates = WhatsAppTemplate.objects.select_related('provider').filter(

        models.Q(owner=request.user) | models.Q(owner=None)

    ).order_by('-id')

    message_templates = MessageTemplate.objects.filter(owner=request.user).order_by('-created_at')

    whatsapp_providers = WhatsAppProvider.objects.filter(is_active=True)

    email_providers = EmailProvider.objects.filter(is_active=True) if request.user.is_staff else None



    context = {

        'email_templates': email_templates,

        'whatsapp_templates': whatsapp_templates,

        'message_templates': message_templates,

        'whatsapp_providers': whatsapp_providers,

        'email_providers': email_providers,

    }

    return render(request, 'campaigns/manage_templates.html', context)



@login_required

def template_email_builder(request, template_id=None):

    """

    Render the visual email builder.

    If template_id is provided load existing template data for editing.

    """

    existing = None

    if template_id:

        if request.user.is_staff:

            existing = EmailTemplate.objects.filter(id=template_id).first()

        else:

            existing = EmailTemplate.objects.filter(id=template_id, owner=request.user).first()

        if not existing:

            messages.error(request, 'Template not found.')

            return redirect('manage_templates')



    if request.user.is_staff:
        providers = EmailProvider.objects.filter(is_active=True)
    else:
        providers = EmailProvider.objects.filter(
            models.Q(owner=request.user) | models.Q(owner__isnull=True),
            is_active=True,
        )

    email_templates = EmailTemplate.objects.filter(

        models.Q(owner=request.user) | models.Q(owner=None)

    ).order_by('-created_at')

    return render(request, 'campaigns/template_email_builder.html', {

        'existing': existing,

        'providers': providers,

        'email_templates': email_templates,

    })


@login_required
def email_builder(request, campaign_id):
    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
    return render(request, 'campaigns/email_builder.html', {
        'campaign': campaign,
        'save_url': reverse('save_email_design', kwargs={'campaign_id': campaign.id}),
        'back_url': reverse('edit_campaign', kwargs={'campaign_id': campaign.id}),
        'test_url': reverse('email_builder_test'),
    })


@login_required
def save_email_design(request, campaign_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required.'}, status=405)

    campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

    html = (payload.get('html') or '').strip()
    design = payload.get('design')

    if not html:
        return JsonResponse({'error': 'HTML content is required.'}, status=400)

    campaign.html_content = html
    campaign.design_json = design
    campaign.save(update_fields=['html_content', 'design_json'])

    return JsonResponse({'success': True, 'message': 'Email design saved successfully.'})



@login_required

def email_builder_delete(request):

    if request.method != 'POST':

        return JsonResponse({'error': 'POST required'}, status=405)



    template_id = request.POST.get('template_id')

    if request.user.is_staff:

        tmpl = EmailTemplate.objects.filter(id=template_id).first()

    else:

        tmpl = EmailTemplate.objects.filter(id=template_id, owner=request.user).first()



    if not tmpl:

        return JsonResponse({'error': 'Template not found.'}, status=404)



    tmpl.delete()

    return JsonResponse({'success': True})



@login_required

def email_builder_save(request):

    """

    AJAX POST endpoint. Receives JSON with template data,

    generates HTML, saves EmailTemplate record.

    Returns JSON with template_id on success.

    """

    if request.method != 'POST':

        return JsonResponse({'error': 'POST required'}, status=405)



    import json



    try:

        data = json.loads(request.body)

    except json.JSONDecodeError:

        return JsonResponse({'error': 'Invalid JSON'}, status=400)



    name = data.get('name', '').strip()

    subject = data.get('subject', '').strip()

    html_content = data.get('html_content', '').strip()

    design_json = data.get('design_json')

    template_id = data.get('template_id')

    provider_id = data.get('provider_id')



    if not name or not subject or not html_content:

        return JsonResponse({'error': 'Name, subject and content are required.'}, status=400)



    provider = None
    provider_queryset = EmailProvider.objects.filter(is_active=True)
    if not request.user.is_staff:
        provider_queryset = provider_queryset.filter(
            models.Q(owner=request.user) | models.Q(owner__isnull=True)
        )

    if provider_id:
        provider = provider_queryset.filter(id=provider_id).first()
        if not provider:
            return JsonResponse({'error': 'Selected email provider is not available.'}, status=400)



    if template_id:

        if request.user.is_staff:

            tmpl = EmailTemplate.objects.filter(id=template_id).first()

        else:

            tmpl = EmailTemplate.objects.filter(id=template_id, owner=request.user).first()

        if not tmpl:

            return JsonResponse({'error': 'Template not found.'}, status=404)

        tmpl.name = name

        tmpl.subject = subject

        tmpl.body_text = html_content
        tmpl.html_content = html_content
        tmpl.design_json = design_json

        tmpl.provider = provider

        tmpl.save()

    else:
        tmpl = EmailTemplate.objects.create(

            name=name,

            subject=subject,

            body_text=html_content,
            html_content=html_content,
            design_json=design_json,

            provider=provider,

            owner=request.user if not request.user.is_staff else None,

            is_active=True,

        )



    return JsonResponse({'success': True, 'template_id': tmpl.id, 'message': f'Template "{tmpl.name}" saved successfully.'})



@login_required
def email_builder_test(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    import json

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    recipient = data.get('recipient', '').strip()
    subject = data.get('subject', '').strip()
    html_content = data.get('html_content', '').strip()
    provider_id = data.get('provider_id')

    if not recipient or not subject or not html_content:
        return JsonResponse({'error': 'Recipient, subject, and template HTML are required.'}, status=400)

    provider = None
    if provider_id:
        provider = EmailProvider.objects.filter(id=provider_id).first()
    if not provider:
        provider = EmailProvider.objects.filter(is_active=True).first()

    if not provider:
        return JsonResponse({'error': 'No active email provider found. Please configure one first.'}, status=400)

    success, message = send_custom_email(
        provider,
        subject,
        html_content,
        [recipient],
        from_email=provider.from_email,
        html_message=True,
    )

    if success:
        return JsonResponse({'success': True, 'message': message})
    return JsonResponse({'error': message}, status=500)


def track_email_open(request, campaign_id, contact_id):
    campaign = get_object_or_404(Campaign, id=campaign_id)
    contact = get_object_or_404(Contact, id=contact_id)

    pixel_data = (
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00'
        b'\x00\x00\x00\xff\xff\xff!\xf9\x04\x01'
        b'\x00\x00\x00\x00,\x00\x00\x00\x00\x01'
        b'\x00\x01\x00\x00\x02\x02D\x01\x00;'
    )

    if campaign.target_group_id and contact.group_id != campaign.target_group_id:
        return HttpResponse(pixel_data, content_type='image/gif')

    Campaign.objects.filter(id=campaign.id).update(opens_count=F('opens_count') + 1)
    CampaignOpenEvent.objects.create(campaign=campaign, contact=contact)

    return HttpResponse(pixel_data, content_type='image/gif')

@login_required
def manage_sms(request):

    if not request.user.is_staff:

        raise PermissionDenied



    if request.method == 'POST':

        action = request.POST.get('action')



        if action == 'create_provider':

            name = request.POST.get('name', '').strip()

            api_key = request.POST.get('api_key', '').strip()

            username = request.POST.get('username', '').strip()

            sender_id = request.POST.get('sender_id', '').strip()



            if not (name and api_key and username):

                messages.error(request, 'Please complete all required SMS provider fields.')

            else:

                SMSProvider.objects.create(

                    name=name,

                    api_key=api_key,

                    username=username,

                    sender_id=sender_id,

                    is_active=False,

                )

                messages.success(request, f'SMS provider "{name}" created successfully.')



        elif action == 'toggle_provider':

            provider_id = request.POST.get('provider_id')

            provider = SMSProvider.objects.filter(id=provider_id).first()

            if provider:

                provider.is_active = not provider.is_active

                provider.save()

                state = 'activated' if provider.is_active else 'deactivated'

                messages.success(request, f'SMS provider "{provider.name}" has been {state}.')


        elif action == 'update_provider':

            provider_id = request.POST.get('provider_id')

            provider = SMSProvider.objects.filter(id=provider_id).first()

            if provider:

                name = request.POST.get('name', provider.name).strip() or provider.name

                api_key = request.POST.get('api_key', '').strip()

                username = request.POST.get('username', '').strip()

                sender_id = request.POST.get('sender_id', '').strip()

                if not (api_key and username):

                    messages.error(request, 'Please complete all required SMS provider fields.')

                    return redirect(f"{reverse('manage_sms')}?edit_provider_id={provider.id}")

                provider.name = name

                provider.api_key = api_key

                provider.username = username

                provider.sender_id = sender_id

                provider.save()

                messages.success(request, f'SMS provider "{provider.get_name_display()}" updated successfully.')

                return redirect('manage_sms')

            else:

                messages.error(request, 'SMS provider not found.')


        elif action == 'delete_provider':

            provider_id = request.POST.get('provider_id')

            provider = SMSProvider.objects.filter(id=provider_id).first()

            if provider:

                provider.delete()

                messages.success(request, f'SMS provider "{provider.name}" has been deleted.')



        return redirect('manage_sms')



    edit_provider = None

    if request.method == 'GET':

        edit_provider_id = request.GET.get('edit_provider_id')

        if edit_provider_id:

            edit_provider = SMSProvider.objects.filter(id=edit_provider_id).first()

            if not edit_provider:

                messages.error(request, 'SMS provider not found.')


    providers = SMSProvider.objects.order_by('-id')

    return render(request, 'campaigns/manage_sms.html', {'providers': providers, 'edit_provider': edit_provider})



@login_required

def manage_whatsapp(request):

    if not request.user.is_staff:

        raise PermissionDenied



    if request.method == 'POST':

        action = request.POST.get('action')



        if action == 'create_provider':

            provider_type = request.POST.get('provider_type', 'meta').strip()

            name = request.POST.get('name', '').strip() or ('Meta Cloud API' if provider_type == 'meta' else 'Infobip WhatsApp')

            access_token = request.POST.get('access_token', '').strip()

            phone_number_id = request.POST.get('phone_number_id', '').strip()

            waba_id = request.POST.get('waba_id', '').strip()

            infobip_base_url = request.POST.get('infobip_base_url', '').strip()

            infobip_sender = request.POST.get('infobip_sender', '').strip()



            if provider_type == 'infobip':

                if not (access_token and infobip_base_url and infobip_sender):

                    messages.error(request, 'Please complete all required Infobip WhatsApp provider fields.')

                else:

                    WhatsAppProvider.objects.create(

                        provider_type=provider_type,

                        name=name,

                        access_token=access_token,

                        infobip_base_url=infobip_base_url,

                        infobip_sender=infobip_sender,

                        is_active=False,

                    )

                    messages.success(request, 'Infobip WhatsApp provider created successfully.')

            else:

                if not (access_token and phone_number_id and waba_id):

                    messages.error(request, 'Please complete all required WhatsApp provider fields.')

                else:

                    WhatsAppProvider.objects.create(

                        provider_type=provider_type,

                        name=name,

                        access_token=access_token,

                        phone_number_id=phone_number_id,

                        waba_id=waba_id,

                        is_active=False,

                    )

                    messages.success(request, 'WhatsApp provider created successfully.')



        elif action == 'toggle_provider':

            provider_id = request.POST.get('provider_id')

            provider = WhatsAppProvider.objects.filter(id=provider_id).first()

            if provider:

                provider.is_active = not provider.is_active

                provider.save()

                state = 'activated' if provider.is_active else 'deactivated'

                messages.success(request, f'WhatsApp provider "{provider.name}" has been {state}.')


        elif action == 'test_provider':

            provider_id = request.POST.get('provider_id')

            provider = WhatsAppProvider.objects.filter(id=provider_id).first()

            if provider:
                if provider.provider_type == 'meta':
                    success, detail = test_whatsapp_meta_connection(provider)
                elif provider.provider_type == 'infobip':
                    success, detail = test_whatsapp_infobip_connection(provider)
                else:
                    success, detail = False, 'Test connection not supported for this provider type yet.'

                if success:
                    messages.success(request, f'WhatsApp provider "{provider.name}" connection successful. {detail}')
                else:
                    messages.error(request, f'Connection test failed for "{provider.name}": {detail}')
            else:
                messages.error(request, 'WhatsApp provider not found.')


        elif action == 'update_provider':

            provider_id = request.POST.get('provider_id')

            provider = WhatsAppProvider.objects.filter(id=provider_id).first()

            if provider:

                provider_type = request.POST.get('provider_type', provider.provider_type).strip()

                name = request.POST.get('name', provider.name).strip() or provider.name

                access_token = request.POST.get('access_token', '').strip()

                phone_number_id = request.POST.get('phone_number_id', '').strip()

                waba_id = request.POST.get('waba_id', '').strip()

                infobip_base_url = request.POST.get('infobip_base_url', '').strip()

                infobip_sender = request.POST.get('infobip_sender', '').strip()


                if provider_type == 'infobip':

                    if not (access_token and infobip_base_url and infobip_sender):

                        messages.error(request, 'Please complete all required Infobip WhatsApp provider fields.')

                        return redirect(f"{reverse('manage_whatsapp')}?edit_provider_id={provider.id}")

                    provider.provider_type = provider_type

                    provider.name = name

                    provider.access_token = access_token

                    provider.infobip_base_url = infobip_base_url

                    provider.infobip_sender = infobip_sender

                    provider.phone_number_id = ''

                    provider.waba_id = ''

                else:

                    if not (access_token and phone_number_id and waba_id):

                        messages.error(request, 'Please complete all required WhatsApp provider fields.')

                        return redirect(f"{reverse('manage_whatsapp')}?edit_provider_id={provider.id}")

                    provider.provider_type = provider_type

                    provider.name = name

                    provider.access_token = access_token

                    provider.phone_number_id = phone_number_id

                    provider.waba_id = waba_id

                    provider.infobip_base_url = ''

                    provider.infobip_sender = ''

                provider.save()

                messages.success(request, f'WhatsApp provider "{provider.name}" updated successfully.')

                return redirect('manage_whatsapp')

            else:

                messages.error(request, 'WhatsApp provider not found.')


        elif action == 'delete_provider':

            provider_id = request.POST.get('provider_id')

            provider = WhatsAppProvider.objects.filter(id=provider_id).first()

            if provider:

                provider.delete()

                messages.success(request, f'WhatsApp provider "{provider.name}" has been deleted.')



        elif action == 'create_template':

            provider_id = request.POST.get('provider_id')

            name = request.POST.get('name', '').strip()

            category = request.POST.get('category', 'MARKETING').strip() or 'MARKETING'

            language_code = request.POST.get('language_code', 'en_US').strip() or 'en_US'

            body_text = request.POST.get('body_text', '').strip()



            provider = WhatsAppProvider.objects.filter(id=provider_id).first()

            if not (provider and name and body_text):

                messages.error(request, 'Please select a provider and provide all required template details.')

            else:

                WhatsAppTemplate.objects.create(

                    provider=provider,

                    owner=request.user,

                    name=name,

                    category=category,

                    language_code=language_code,

                    body_text=body_text,

                )

                messages.success(request, f'WhatsApp template "{name}" created successfully.')



        elif action == 'delete_template':

            template_id = request.POST.get('template_id')

            template = WhatsAppTemplate.objects.filter(id=template_id).first()

            if template:

                template.delete()

                messages.success(request, f'WhatsApp template "{template.name}" has been deleted.')



        return redirect('manage_whatsapp')



    edit_provider = None

    if request.method == 'GET':

        edit_provider_id = request.GET.get('edit_provider_id')

        if edit_provider_id:

            edit_provider = WhatsAppProvider.objects.filter(id=edit_provider_id).first()

            if not edit_provider:

                messages.error(request, 'WhatsApp provider not found.')


    providers = WhatsAppProvider.objects.order_by('-id')

    templates = WhatsAppTemplate.objects.select_related('provider').order_by('-id')

    return render(request, 'campaigns/manage_whatsapp.html', {'providers': providers, 'templates': templates, 'edit_provider': edit_provider})



@login_required

def my_email_providers(request):

    if request.method == 'POST':

        action = request.POST.get('action')



        if action == 'create_provider':

            name = request.POST.get('name', '').strip()

            smtp_host = request.POST.get('smtp_host', '').strip()

            smtp_port = request.POST.get('smtp_port', '').strip()

            smtp_username = request.POST.get('smtp_username', '').strip()

            smtp_password = request.POST.get('smtp_password', '').strip()

            use_tls = request.POST.get('use_tls') == 'on'

            use_ssl = request.POST.get('use_ssl') == 'on'

            from_email = request.POST.get('from_email', '').strip()



            if not (name and smtp_host and smtp_port and smtp_username and smtp_password and from_email):

                messages.error(request, 'Please complete all required SMTP fields.')

            else:

                try:

                    EmailProvider.objects.create(

                        name=name,

                        smtp_host=smtp_host,

                        smtp_port=int(smtp_port),

                        smtp_username=smtp_username,

                        smtp_password=smtp_password,

                        use_tls=use_tls,

                        use_ssl=use_ssl,

                        from_email=from_email,

                        is_active=False,

                        owner=request.user,

                    )

                    messages.success(request, f'Email provider "{name}" created successfully.')

                except ValueError:

                    messages.error(request, 'SMTP port must be a valid number.')



        elif action == 'toggle_provider':

            provider_id = request.POST.get('provider_id')

            provider = EmailProvider.objects.filter(id=provider_id, owner=request.user).first()

            if provider:

                provider.is_active = not provider.is_active

                provider.save()

                state = 'activated' if provider.is_active else 'deactivated'

                messages.success(request, f'Provider "{provider.name}" has been {state}.')



        elif action == 'delete_provider':

            provider_id = request.POST.get('provider_id')

            provider = EmailProvider.objects.filter(id=provider_id, owner=request.user).first()

            if provider:

                provider.delete()

                messages.success(request, f'Provider "{provider.name}" has been deleted.')



        elif action == 'update_provider':

            provider_id = request.POST.get('provider_id')

            provider = EmailProvider.objects.filter(id=provider_id, owner=request.user).first()

            if provider:

                name = request.POST.get('name', '').strip() or provider.name

                smtp_host = request.POST.get('smtp_host', '').strip()

                smtp_port = request.POST.get('smtp_port', '').strip()

                smtp_username = request.POST.get('smtp_username', '').strip()

                smtp_password = request.POST.get('smtp_password', '').strip()

                use_tls = request.POST.get('use_tls') == 'on'

                use_ssl = request.POST.get('use_ssl') == 'on'

                from_email = request.POST.get('from_email', '').strip()


                if not (name and smtp_host and smtp_port and smtp_username and smtp_password and from_email):

                    messages.error(request, 'Please complete all required SMTP fields.')

                    return redirect(f"{reverse('my_email_providers')}?edit_provider_id={provider.id}")

                try:

                    provider.name = name

                    provider.smtp_host = smtp_host

                    provider.smtp_port = int(smtp_port)

                    provider.smtp_username = smtp_username

                    provider.smtp_password = smtp_password

                    provider.use_tls = use_tls

                    provider.use_ssl = use_ssl

                    provider.from_email = from_email

                    provider.save()

                    messages.success(request, f'Email provider "{name}" updated successfully.')

                except ValueError:

                    messages.error(request, 'SMTP port must be a valid number.')

                    return redirect(f"{reverse('my_email_providers')}?edit_provider_id={provider.id}")

            else:

                messages.error(request, 'Email provider not found.')


        return redirect('my_email_providers')



    edit_provider = None

    if request.method == 'GET':

        edit_provider_id = request.GET.get('edit_provider_id')

        if edit_provider_id:

            edit_provider = EmailProvider.objects.filter(id=edit_provider_id, owner=request.user).first()

            if not edit_provider:

                messages.error(request, 'Email provider not found.')


    providers = EmailProvider.objects.filter(owner=request.user).order_by('-id')

    return render(request, 'campaigns/my_email_providers.html', {'providers': providers, 'edit_provider': edit_provider})



@login_required

def customer_create_group(request):

    groups = Group.objects.filter(user=request.user).order_by('-created_at')



    if request.method == 'POST':

        name = request.POST.get('name', '').strip()

        description = request.POST.get('description', '').strip()



        if not name:

            messages.error(request, 'Please provide a group name.')

            return redirect('customer_create_group')



        Group.objects.create(user=request.user, name=name, description=description)

        messages.success(request, f'Group "{name}" created. Import contacts next.')

        return redirect('upload_contacts')



    return render(request, 'campaigns/customer_groups.html', {'groups': groups})



@login_required

def create_campaign(request, campaign_id=None):

    """Handles logic for creating, editing, saving, and launching unified multi-channel campaigns."""

    campaign = None

    is_edit = False

    if campaign_id is not None:

        campaign = Campaign.objects.filter(id=campaign_id).first()

        if not campaign or (campaign.user != request.user and not request.user.is_staff):

            messages.error(request, 'Campaign not found.')

            return redirect('campaigns_overview')

        if campaign.status != 'draft':

            messages.error(request, 'Only draft campaigns can be edited.')

            return redirect('campaigns_overview')

        is_edit = True



    if request.method == 'POST':

        action = request.POST.get('action', 'launch')

        form = CampaignForm(request.POST, user=request.user, instance=campaign)

        context = {'form': form, 'TIME_ZONE': django_settings.TIME_ZONE, 'is_edit': is_edit}

        if form.is_valid():

            campaign = form.save(commit=False)

            campaign.user = request.user

            selected_sms_template = form.cleaned_data.get('sms_template')



            if action == 'save_draft':

                if selected_sms_template:

                    campaign.message_body = selected_sms_template.body

                campaign.status = 'draft'

                scheduled_time_str = request.POST.get('scheduled_time', '').strip()

                if scheduled_time_str:

                    scheduled_dt = parse_datetime(scheduled_time_str)

                    if timezone.is_naive(scheduled_dt):

                        scheduled_dt = timezone.make_aware(scheduled_dt)

                    campaign.scheduled_time = scheduled_dt

                campaign.save()

                messages.success(request, 'Draft saved successfully.')

                return redirect('campaigns_overview')



            if campaign.send_sms and not selected_sms_template:

                messages.error(request, 'Select an SMS template before launching a campaign with SMS enabled.')

                return render(request, 'campaigns/create_campaign.html', context)

            if campaign.send_whatsapp and not campaign.whatsapp_template:

                messages.error(request, 'Select a WhatsApp template before launching a campaign with WhatsApp enabled.')

                return render(request, 'campaigns/create_campaign.html', context)

            if campaign.send_email and not (campaign.email_template or campaign.html_content):

                messages.error(request, 'Select an email template or save a custom email design before launching an email campaign.')

                return render(request, 'campaigns/create_campaign.html', context)



            if selected_sms_template:

                campaign.message_body = selected_sms_template.body

            else:

                campaign.message_body = ''



            if not campaign.target_group:

                messages.error(request, 'Please select a target group to launch the campaign.')

                return render(request, 'campaigns/create_campaign.html', context)



            contacts = campaign.target_group.contacts.all()

            sms_recipients = [c.phone_number for c in contacts if c.phone_number]

            whatsapp_recipients = sms_recipients

            email_recipients = [c.email for c in contacts if c.email]



            selected_channels = []

            if campaign.send_sms:

                selected_channels.append('sms')

            if campaign.send_whatsapp:

                selected_channels.append('whatsapp')

            if campaign.send_email:

                selected_channels.append('email')



            if not selected_channels:

                messages.error(request, 'Select at least one channel for this campaign.')

                return render(request, 'campaigns/create_campaign.html', context)



            if campaign.send_sms and not campaign.sms_server:

                messages.error(request, 'No SMS provider selected. Please contact support to activate an SMS provider.')

                return render(request, 'campaigns/create_campaign.html', context)



            if campaign.send_whatsapp and not campaign.whatsapp_server:

                messages.error(request, 'No WhatsApp provider selected. Please contact support to activate a WhatsApp provider.')

                return render(request, 'campaigns/create_campaign.html', context)



            unit_count = 0

            if campaign.send_sms:

                unit_count += len(sms_recipients)

            if campaign.send_whatsapp:

                unit_count += len(whatsapp_recipients)

            if campaign.send_email:

                unit_count += len(email_recipients)



            quota = getattr(request.user, 'quota', None)

            if quota is None:

                quota = UserQuota.objects.create(user=request.user)



            if unit_count > (quota.max_units - quota.units_used):

                messages.error(request, 'Your campaign exceeds the remaining free-tier quota. Please reduce recipients or channels.')

                return render(request, 'campaigns/create_campaign.html', context)



            if campaign.send_email and not campaign.email_server:

                default_email_provider = EmailProvider.objects.filter(owner=request.user, is_active=True).order_by('-id').first()

                if not default_email_provider:

                    default_email_provider = EmailProvider.objects.filter(owner__isnull=True, is_active=True).order_by('-id').first()

                if default_email_provider:

                    campaign.email_server = default_email_provider

                else:

                    messages.error(request, 'No active email provider is configured. Activate an SMTP provider first.')

                    return render(request, 'campaigns/create_campaign.html', context)



            if campaign.send_email and campaign.email_server and not campaign.email_server.is_active:

                messages.error(request, 'The selected email provider is inactive. Please choose an active provider.')

                return render(request, 'campaigns/create_campaign.html', context)



            if campaign.send_email and not email_recipients:

                messages.error(request, 'Email sending requires at least one valid recipient email address.')

                return render(request, 'campaigns/create_campaign.html', context)



            send_mode = request.POST.get('send_mode', 'now')

            scheduled_time_str = request.POST.get('scheduled_time', '').strip()

            if send_mode == 'schedule':

                if not scheduled_time_str:

                    messages.error(request, 'Please select a scheduled date and time.')

                    return render(request, 'campaigns/create_campaign.html', context)



                scheduled_dt = parse_datetime(scheduled_time_str)

                if not scheduled_dt:

                    messages.error(request, 'Invalid date/time format. Please use the date picker.')

                    return render(request, 'campaigns/create_campaign.html', context)



                if timezone.is_naive(scheduled_dt):

                    scheduled_dt = timezone.make_aware(scheduled_dt)



                if scheduled_dt <= timezone.now():

                    messages.error(request, 'Scheduled time must be in the future.')

                    return render(request, 'campaigns/create_campaign.html', context)



                campaign.scheduled_time = scheduled_dt

                campaign.status = 'scheduled'

                campaign.save()

                messages.success(request, f'Campaign scheduled for {scheduled_dt.strftime("%b %d, %Y at %I:%M %p")}.' )

                return redirect('dashboard')



            campaign.status = 'queued'
            campaign.failure_reason = ''
            campaign.save()

            transaction.on_commit(lambda: dispatch_campaign_task.delay(campaign.id))
            messages.success(request, 'Your campaign has been queued and is processing in the background.')
            return redirect('dashboard')

    else:

        form = CampaignForm(user=request.user, instance=campaign)

        context = {'form': form, 'TIME_ZONE': django_settings.TIME_ZONE, 'is_edit': is_edit}



    return render(request, 'campaigns/create_campaign.html', context)



@login_required

def scheduled_campaigns(request):

    """View and manage scheduled campaigns."""

    if request.user.is_staff:

        campaigns = Campaign.objects.filter(status='scheduled').select_related('user', 'target_group').order_by('scheduled_time')

    else:

        campaigns = Campaign.objects.filter(user=request.user, status='scheduled').select_related('target_group').order_by('scheduled_time')



    return render(request, 'campaigns/scheduled_campaigns.html', {

        'campaigns': campaigns,

    })



@login_required

def cancel_campaign(request, campaign_id):

    """Cancel a scheduled campaign."""

    if request.user.is_staff:

        campaign = Campaign.objects.filter(id=campaign_id, status='scheduled').first()

    else:

        campaign = Campaign.objects.filter(id=campaign_id, user=request.user, status='scheduled').first()



    if not campaign:

        messages.error(request, 'Campaign not found or already sent.')

        return redirect('scheduled_campaigns')



    if request.method == 'POST':

        reason = request.POST.get('reason', '').strip()

        campaign.status = 'cancelled'

        campaign.cancel_reason = reason

        campaign.save()

        messages.success(request, f'Campaign "{campaign.title}" has been cancelled.')

        return redirect('scheduled_campaigns')



    return render(request, 'campaigns/cancel_campaign_confirm.html', {'campaign': campaign})



@login_required

def reschedule_campaign(request, campaign_id):

    """Reschedule a scheduled campaign to a new time."""

    if request.user.is_staff:

        campaign = Campaign.objects.filter(id=campaign_id, status='scheduled').first()

    else:

        campaign = Campaign.objects.filter(id=campaign_id, user=request.user, status='scheduled').first()



    if not campaign:

        messages.error(request, 'Campaign not found or cannot be rescheduled.')

        return redirect('scheduled_campaigns')



    if request.method == 'POST':

        new_time_str = request.POST.get('scheduled_time', '').strip()

        new_dt = parse_datetime(new_time_str)

        if not new_dt:

            messages.error(request, 'Invalid date/time.')

            return render(request, 'campaigns/reschedule_campaign.html', {'campaign': campaign})

        if timezone.is_naive(new_dt):

            new_dt = timezone.make_aware(new_dt)

        if new_dt <= timezone.now():

            messages.error(request, 'New scheduled time must be in the future.')

            return render(request, 'campaigns/reschedule_campaign.html', {'campaign': campaign})

        campaign.scheduled_time = new_dt

        campaign.save()

        messages.success(request, f'Campaign rescheduled to {new_dt.strftime("%b %d, %Y at %I:%M %p")}.')

        return redirect('scheduled_campaigns')



    return render(request, 'campaigns/reschedule_campaign.html', {'campaign': campaign})



@login_required

def ai_suggest_view(request):

    """Internal API for AI-powered campaign generation."""

    topic = request.GET.get('topic', 'marketing')

    suggestion = get_ai_campaign_suggestion(topic)

    return JsonResponse({'suggestion': suggestion})



def send_verification_email(user, request):

    token = default_token_generator.make_token(user)

    uid = urlsafe_base64_encode(force_bytes(user.pk))

    activation_path = reverse('activate', kwargs={'uidb64': uid, 'token': token})

    activation_link = f"{django_settings.SITE_URL.rstrip('/')}{activation_path}"



    subject = 'Verify your Greyteeks email address'

    message = f"""Hi {user.first_name or user.username},



Thanks for signing up for Greyteeks. Please verify your email address by clicking the link below:



{activation_link}



If you did not create this account, you can ignore this message.



Thanks,

Greyteeks Team"""



    send_mail(

        subject,

        message,

        django_settings.DEFAULT_FROM_EMAIL,

        [user.email],

        fail_silently=False,

    )





def activate_account(request, uidb64, token):

    try:

        uid = force_str(urlsafe_base64_decode(uidb64))

        user = User.objects.get(pk=uid)

    except (TypeError, ValueError, OverflowError, User.DoesNotExist):

        user = None



    if user is not None and default_token_generator.check_token(user, token):

        if not user.is_active:

            user.is_active = True

            user.save()

            login(request, user)

            messages.success(request, 'Your email has been verified and your account is now active.')

        else:

            messages.info(request, 'Your email is already verified. You are now logged in.')

            login(request, user)

        return redirect('dashboard')



    messages.error(request, 'Verification link is invalid or has expired.')

    return redirect('home')





def register_view(request):

    """Handles new user registration from the home page modal."""

    if request.method == 'GET':

        return render(request, 'home/sign-up.html')



    if request.method == 'POST':

        username = request.POST.get('username') or request.POST.get('email')

        email = request.POST.get('email')

        password = request.POST.get('password1') or request.POST.get('password')

        password_confirm = request.POST.get('password2') or request.POST.get('password_confirm')

        full_name = request.POST.get('name') or request.POST.get('full_name', '')



        if not username or not email or not password:

            messages.error(request, "Email and password are required.")

            return redirect('home')



        if password_confirm and password != password_confirm:

            messages.error(request, "Passwords do not match. Please try again.")

            return redirect('home')



        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():

            messages.error(request, "An account with that email already exists.")

            return redirect('home')



        try:

            user = User.objects.create_user(

                username=username,

                email=email,

                password=password,

                first_name=full_name,

                is_active=False,

            )

            send_verification_email(user, request)

            messages.success(request, "Your account has been created. Check your email to verify your address before logging in.")

            return redirect('home')

        except IntegrityError:

            messages.error(request, "That email is already taken. Please try another.")

            return redirect('home')



    return redirect('home')


from billing.models import PricingPlan

def pricing_view(request):
    plans = PricingPlan.objects.filter(is_active=True).order_by('price_kes')
    return render(request, 'home/pricing.html', {'plans': plans})

def service_view(request):
    return render(request, 'home/service.html')

def faq_view(request):
    return render(request, 'home/faq.html')

@login_required
def api_documentation_view(request):
    return render(request, 'campaigns/api_documentation.html')
