import africastalking
import requests
from django.core.mail import EmailMessage, get_connection

def send_at_sms(provider_instance, destination_phone, message):
    """Sends a single SMS (for testing)"""
    africastalking.initialize(provider_instance.username, provider_instance.api_key)
    sms = africastalking.SMS
    try:
        response = sms.send(message, [destination_phone], provider_instance.sender_id or None)
        print(f"Single Send Response: {response}")
        return True
    except Exception as e:
        print(f"Single Send Error: {e}")
        return False

def send_bulk_at_sms(provider_instance, phone_numbers, message):
    """Sends bulk SMS to a list of numbers"""
    africastalking.initialize(provider_instance.username, provider_instance.api_key)
    sms = africastalking.SMS
    try:
        response = sms.send(message, phone_numbers, provider_instance.sender_id or None)
        print(f"Bulk Send Response: {response}")
        return True
    except Exception as e:
        print(f"Bulk Send Error: {e}")
        return False
    

def send_bulk_twilio_sms(provider_instance, phone_numbers, message):
    """Send bulk SMS via Twilio REST API."""
    success_count = 0
    account_sid = provider_instance.username
    auth_token = provider_instance.api_key
    from_number = provider_instance.sender_id or provider_instance.username
    url = f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json'
    for number in phone_numbers:
        try:
            response = requests.post(
                url,
                data={'From': from_number, 'To': number, 'Body': message},
                auth=(account_sid, auth_token),
                timeout=30,
            )
            if response.status_code in (200, 201):
                success_count += 1
            else:
                print(f"Twilio SMS Error for {number}: {response.text}")
        except Exception as e:
            print(f"Twilio SMS Exception for {number}: {e}")
    return success_count == len(phone_numbers)


def send_bulk_infobip_sms(provider_instance, phone_numbers, message):
    """Send bulk SMS via Infobip REST API."""
    api_key = provider_instance.api_key
    base_url = provider_instance.username
    sender = provider_instance.sender_id or 'Greyteeks'
    url = f'https://{base_url}/sms/2/text/advanced'
    headers = {
        'Authorization': f'App {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    destinations = [{'to': number} for number in phone_numbers]
    payload = {
        'messages': [{
            'from': sender,
            'destinations': destinations,
            'text': message,
        }]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        messages = data.get('messages', [])
        failed = [m for m in messages if m.get('status', {}).get('groupName') not in ('PENDING', 'DELIVERED', 'SENT')]
        print(f"Infobip SMS Response: {response.status_code} — {len(messages)} sent, {len(failed)} failed")
        return len(failed) == 0
    except Exception as e:
        print(f"Infobip SMS Exception: {e}")
        return False


def send_whatsapp_meta_message(provider_instance, destination_phone, message_text):
    """Sends a WhatsApp message via Meta Cloud API"""
    url = f"https://graph.facebook.com/v17.0/{provider_instance.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {provider_instance.access_token}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": destination_phone,
        "type": "text",
        "text": {"body": message_text},
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200
    except Exception as e:
        print(f"WhatsApp Error: {e}")
        return False


def send_whatsapp_infobip_message(provider_instance, destination_phone, message_text):
    """Send a WhatsApp message via Infobip API."""
    url = f"https://{provider_instance.infobip_base_url}/whatsapp/1/message/text"
    headers = {
        "Authorization": f"App {provider_instance.access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "from": provider_instance.infobip_sender,
        "to": destination_phone,
        "content": {
            "text": message_text,
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Infobip WhatsApp Response: {response.status_code} — {response.text[:200]}")
        return response.status_code in (200, 201)
    except Exception as e:
        print(f"Infobip WhatsApp Error: {e}")
        return False


def route_sms(provider_instance, phone_numbers, message):
    """Route SMS sending to the correct provider service based on provider type."""
    if not provider_instance:
        print("SMS Error: missing provider instance")
        return False
    name = provider_instance.name
    if name == 'africas_talking':
        return send_bulk_at_sms(provider_instance, phone_numbers, message)
    elif name == 'twilio':
        return send_bulk_twilio_sms(provider_instance, phone_numbers, message)
    elif name == 'infobip':
        return send_bulk_infobip_sms(provider_instance, phone_numbers, message)
    else:
        print(f"Unknown SMS provider: {name}")
        return False


def route_whatsapp(provider_instance, destination_phone, message_text):
    """Route WhatsApp sending to the correct provider service."""
    if not provider_instance:
        print("WhatsApp Error: missing provider instance")
        return False
    provider_type = getattr(provider_instance, 'provider_type', 'meta')
    if provider_type == 'infobip':
        return send_whatsapp_infobip_message(provider_instance, destination_phone, message_text)
    return send_whatsapp_meta_message(provider_instance, destination_phone, message_text)


def send_custom_email(provider_instance, subject, message, recipient_list, from_email=None):
    """Sends email using the configured SMTP provider via Django EmailBackend."""
    if not recipient_list:
        print("Email Error: no recipients provided")
        return False

    connection = get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=provider_instance.smtp_host,
        port=provider_instance.smtp_port,
        username=provider_instance.smtp_username,
        password=provider_instance.smtp_password,
        use_tls=provider_instance.use_tls,
        use_ssl=provider_instance.use_ssl,
        fail_silently=False,
    )

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=from_email or provider_instance.from_email,
        to=recipient_list,
        connection=connection,
    )

    try:
        email.send(fail_silently=False)
        connection.close()
        print(f"Email sent to {len(recipient_list)} recipients via {provider_instance.name}")
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        connection.close()
        return False


def send_bulk_email(provider_instance, subject, body, recipients, from_email=None):
    return send_custom_email(provider_instance, subject, body, recipients, from_email=from_email)