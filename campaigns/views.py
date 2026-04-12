from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from contacts_app.models import Contact, Group
from accounts.models import UserQuota
from .models import Campaign
from .forms import CampaignForm
from .utils import get_ai_campaign_suggestion
from providers.models import EmailProvider
from providers.services import send_bulk_at_sms, send_whatsapp_meta_message, send_custom_email

def home_view(request):
    """Public landing page. Redirects authenticated users to their dashboard."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'campaigns/home.html')

@login_required
def dashboard(request):
    """
    Role-based Dashboard:
    - Admins (staff) see global system-wide statistics.
    - Customers see only their personal marketing data.
    """
    if request.user.is_staff:
        # Admin View: Aggregated system data
        total_campaigns = Campaign.objects.count()
        total_contacts = Contact.objects.count()
        total_groups = Group.objects.count()
        total_users = User.objects.count()
        recent_campaigns = Campaign.objects.order_by('-created_at')[:10]
        total_sms_sent = Campaign.objects.filter(send_sms=True, status='sent').count()
        total_whatsapp_sent = Campaign.objects.filter(send_whatsapp=True, status='sent').count()
        total_email_sent = Campaign.objects.filter(send_email=True, status='sent').count()
        user_quota = None
        quota_progress = None
    else:
        # Customer View: Isolated personal data
        user_campaigns = Campaign.objects.filter(user=request.user)
        total_campaigns = user_campaigns.count()
        total_groups = Group.objects.filter(user=request.user).count()
        total_contacts = Contact.objects.filter(group__user=request.user).count()
        recent_campaigns = user_campaigns.order_by('-created_at')[:5]
        total_sms_sent = user_campaigns.filter(send_sms=True, status='sent').count()
        total_whatsapp_sent = user_campaigns.filter(send_whatsapp=True, status='sent').count()
        total_email_sent = user_campaigns.filter(send_email=True, status='sent').count()
        user_quota = getattr(request.user, 'quota', None)
        quota_progress = None
        if user_quota and user_quota.max_units:
            quota_progress = int((user_quota.units_used / user_quota.max_units) * 100)

    context = {
        'total_campaigns': total_campaigns,
        'total_contacts': total_contacts,
        'total_groups': total_groups,
        'total_users': total_users if request.user.is_staff else None,
        'recent_campaigns': recent_campaigns,
        'total_sms_sent': total_sms_sent,
        'total_whatsapp_sent': total_whatsapp_sent,
        'total_email_sent': total_email_sent,
    }
    return render(request, 'campaigns/dashboard.html', context)

def about_view(request):
    return render(request, 'campaigns/about.html')


def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        preferred_date = request.POST.get('preferred_date', '').strip()
        preferred_time = request.POST.get('preferred_time', '').strip()

        if not name or not email or not subject or not message:
            messages.error(request, 'Please complete all required fields.')
        else:
            messages.success(request, f'Thanks {name}, your demo request is booked for {preferred_date} at {preferred_time}.')
            return redirect('contact')

    return render(request, 'campaigns/contact_us.html')

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
def create_campaign(request):
    """Handles logic for creating and launching unified multi-channel campaigns."""
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.user = request.user

            if not campaign.target_group:
                messages.error(request, 'Please select a target group to launch the campaign.')
                return render(request, 'campaigns/create_campaign.html', {'form': form})

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
                return render(request, 'campaigns/create_campaign.html', {'form': form})

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
                return render(request, 'campaigns/create_campaign.html', {'form': form})

            if campaign.send_email and not campaign.email_server:
                default_email_provider = EmailProvider.objects.filter(is_active=True).order_by('-id').first()
                if default_email_provider:
                    campaign.email_server = default_email_provider
                else:
                    messages.error(request, 'No active email provider is configured. Activate an SMTP provider first.')
                    return render(request, 'campaigns/create_campaign.html', {'form': form})

            if campaign.send_email and campaign.email_server and not campaign.email_server.is_active:
                messages.error(request, 'The selected email provider is inactive. Please choose an active provider.')
                return render(request, 'campaigns/create_campaign.html', {'form': form})

            if campaign.send_email and not email_recipients:
                messages.error(request, 'Email sending requires at least one valid recipient email address.')
                return render(request, 'campaigns/create_campaign.html', {'form': form})

            campaign.status = 'draft'
            campaign.save()

            channel_success = True

            if campaign.send_sms:
                if campaign.sms_server and sms_recipients:
                    sms_sent = send_bulk_at_sms(campaign.sms_server, sms_recipients, campaign.message_body)
                    channel_success = channel_success and sms_sent
                else:
                    channel_success = False

            if campaign.send_whatsapp:
                if campaign.whatsapp_server and whatsapp_recipients:
                    outbound_text = campaign.whatsapp_template.body_text if campaign.whatsapp_template else campaign.message_body
                    for number in whatsapp_recipients:
                        whatsapp_sent = send_whatsapp_meta_message(campaign.whatsapp_server, number, outbound_text)
                        if not whatsapp_sent:
                            channel_success = False
                            break
                else:
                    channel_success = False

            if campaign.send_email:
                if campaign.email_server and email_recipients:
                    outbound_subject = campaign.email_template.subject if campaign.email_template else campaign.title
                    outbound_body = campaign.email_template.body_text if campaign.email_template else campaign.message_body
                    email_sent = send_custom_email(
                        campaign.email_server,
                        outbound_subject,
                        outbound_body,
                        email_recipients,
                        from_email=campaign.email_server.from_email
                    )
                    channel_success = channel_success and email_sent
                else:
                    channel_success = False

            campaign.status = 'sent' if channel_success else 'failed'
            campaign.save()

            if channel_success:
                quota.units_used += unit_count
                quota.save()
                messages.success(request, 'Campaign launched successfully!')
            else:
                messages.error(request, 'One or more channels failed to send. Review your provider setup and try again.')

            return redirect('dashboard')
    else:
        form = CampaignForm()

    return render(request, 'campaigns/create_campaign.html', {'form': form})

@login_required
def ai_suggest_view(request):
    """Internal API for AI-powered campaign generation."""
    topic = request.GET.get('topic', 'marketing')
    suggestion = get_ai_campaign_suggestion(topic)
    return JsonResponse({'suggestion': suggestion})

def register_view(request):
    """Handles new user registration from the home page modal."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        full_name = request.POST.get('full_name', '')
        
        if not username or not password:
            messages.error(request, "Username and Password are required.")
            return redirect('home')
            
        try:
            # Create user and assign full name to first_name field
            user = User.objects.create_user(
                username=username, 
                email=email, 
                password=password,
                first_name=full_name
            )
            login(request, user)
            messages.success(request, f"Welcome to Greyteeks, {username}!")
            return redirect('dashboard')
        
        except IntegrityError:
            messages.error(request, "That username is already taken. Please try another.")
            return redirect('home')
    
    return redirect('home')