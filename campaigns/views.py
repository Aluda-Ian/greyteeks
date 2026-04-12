from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Campaign
from .forms import CampaignForm
from providers.services import send_at_sms, send_bulk_at_sms

# --- MISSING IMPORTS START ---
from providers.services import send_at_sms
from .utils import get_ai_campaign_suggestion
from contacts.models import Contact, Group
# --- MISSING IMPORTS END ---

def dashboard(request):
    total_campaigns = Campaign.objects.count()
    total_contacts = Contact.objects.count()
    total_groups = Group.objects.count()
    
    # Get the last 5 campaigns to show a "Recent Activity" list
    recent_campaigns = Campaign.objects.order_by('-created_at')[:5]

    context = {
        'total_campaigns': total_campaigns,
        'total_contacts': total_contacts,
        'total_groups': total_groups,
        'recent_campaigns': recent_campaigns,
    }
    return render(request, 'campaigns/dashboard.html', context)
def create_campaign(request):
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save()
            
            # If target_group is selected and it's an SMS campaign
            if campaign.channel == 'sms' and campaign.sms_server and campaign.target_group:
                contacts = campaign.target_group.contacts.all()
                phone_numbers = [c.phone_number for c in contacts]
                
                # Send the bulk SMS
                success = send_bulk_at_sms(
                    campaign.sms_server, 
                    phone_numbers, 
                    campaign.message_body
                )
                
                campaign.status = 'sent' if success else 'failed'
                campaign.save()
                
            return redirect('dashboard')
    else:
        form = CampaignForm()
            
    return render(request, 'campaigns/create_campaign.html', {'form': form})

def ai_suggest_view(request):
    """An API endpoint for the 'Generate with AI' button"""
    topic = request.GET.get('topic', 'marketing')
    suggestion = get_ai_campaign_suggestion(topic)
    return JsonResponse({'suggestion': suggestion})