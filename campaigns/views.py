from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from contacts_app.models import Contact, Group
from .models import Campaign
from .forms import CampaignForm
from .utils import get_ai_campaign_suggestion
from providers.services import send_bulk_at_sms, send_whatsapp_meta_message, send_bulk_email

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
    else:
        # Customer View: Isolated personal data
        user_campaigns = Campaign.objects.filter(user=request.user)
        total_campaigns = user_campaigns.count()
        total_groups = Group.objects.filter(user=request.user)
        total_contacts = Contact.objects.filter(group__user=request.user).count()
        recent_campaigns = user_campaigns.order_by('-created_at')[:5]

    context = {
        'total_campaigns': total_campaigns,
        'total_contacts': total_contacts,
        'total_groups': total_groups if request.user.is_staff else total_groups.count(),
        'total_users': total_users if request.user.is_staff else None,
        'recent_campaigns': recent_campaigns,
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
def create_campaign(request):
    """Handles logic for creating and launching SMS or WhatsApp campaigns."""
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.user = request.user
            campaign.save()
            
            if campaign.target_group:
                contacts = campaign.target_group.contacts.all()
                recipients = [c.phone_number for c in contacts if c.phone_number]
                email_recipients = [c.email for c in contacts if c.email]
                success = False

                if campaign.channel == 'sms' and campaign.sms_server:
                    success = send_bulk_at_sms(
                        campaign.sms_server,
                        recipients,
                        campaign.message_body
                    )

                elif campaign.channel == 'whatsapp' and campaign.whatsapp_server:
                    outbound_text = campaign.whatsapp_template.body_text if campaign.whatsapp_template else campaign.message_body
                    for number in recipients:
                        success = send_whatsapp_meta_message(
                            campaign.whatsapp_server,
                            number,
                            outbound_text
                        )
                        if not success:
                            break

                elif campaign.channel == 'email' and campaign.email_server:
                    outbound_subject = campaign.email_template.subject if campaign.email_template else campaign.title
                    outbound_body = campaign.email_template.body_text if campaign.email_template else campaign.message_body
                    success = send_bulk_email(
                        campaign.email_server,
                        outbound_subject,
                        outbound_body,
                        email_recipients,
                        from_email=campaign.email_server.from_email
                    )

                campaign.status = 'sent' if success else 'failed'
                campaign.save()
                
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