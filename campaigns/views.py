from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from contacts_app.models import Contact, Group # Update this import
from .models import Campaign
from .forms import CampaignForm
from .utils import get_ai_campaign_suggestion
from contacts.models import Contact, Group
from providers.services import send_bulk_at_sms, send_whatsapp_meta_message

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
        'recent_campaigns': recent_campaigns,
    }
    return render(request, 'campaigns/dashboard.html', context)

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
                phone_numbers = [c.phone_number for c in contacts]
                
                success = False
                # Handle SMS via Africa's Talking
                if campaign.channel == 'sms' and campaign.sms_server:
                    success = send_bulk_at_sms(
                        campaign.sms_server, 
                        phone_numbers, 
                        campaign.message_body
                    )
                
                # Handle WhatsApp via Meta Cloud API
                elif campaign.channel == 'whatsapp' and campaign.whatsapp_server:
                    for number in phone_numbers:
                        success = send_whatsapp_meta_message(
                            campaign.whatsapp_server, 
                            number, 
                            campaign.message_body
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