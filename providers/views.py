import json

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from contacts_app.models import Contact, Conversation, Message
from django.utils import timezone
from .models import WhatsAppDeliveryLog


@csrf_exempt
def whatsapp_webhook(request):
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if mode == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge)
        return HttpResponse('Verification token mismatch', status=403)

    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, json.JSONDecodeError):
        return HttpResponse('OK')

    entry_list = payload.get('entry', [])
    for entry in entry_list:
        for change in entry.get('changes', []):
            value = change.get('value', {})
            for status in value.get('statuses', []):
                phone = status.get('recipient_id') or status.get('recipient_phone_number') or status.get('to')
                message_id = status.get('id')
                status_type = status.get('status')
                conversation = status.get('conversation', {})
                external_id = conversation.get('id')

                contact = None
                if phone:
                    contact = Contact.objects.filter(phone_number__endswith=phone[-9:]).first()

                log = WhatsAppDeliveryLog.objects.create(
                    campaign=None,
                    contact=contact,
                    provider=None,
                    message_id=message_id or '',
                    status=status_type or 'unknown',
                    external_id=external_id or '',
                    raw_payload=status,
                )
                print(f"Logged WhatsApp status: {log.status} for recipient {phone}")

                if contact and status_type in ('delivered', 'read'):
                    # Keep contact metadata in a simple log for later audits or dashboards.
                    pass

            for incoming in value.get('messages', []):
                sender = incoming.get('from') or incoming.get('wa_id')
                if not sender:
                    continue

                text = ''
                if incoming.get('text'):
                    text = incoming['text'].get('body', '')
                elif incoming.get('interactive'):
                    interactive = incoming.get('interactive', {})
                    text = interactive.get('button', {}).get('text', '') or interactive.get('list_reply', {}).get('title', '')

                if not text:
                    continue

                contact = Contact.objects.filter(phone_number__endswith=sender[-9:]).first()
                if not contact:
                    continue

                conversation, _ = Conversation.objects.get_or_create(
                    user=contact.group.user,
                    contact=contact,
                )
                Message.objects.create(
                    conversation=conversation,
                    direction='inbound',
                    channel='whatsapp',
                    content=text,
                )
                conversation.save(update_fields=['last_updated'])

    return JsonResponse({'status': 'received'})
