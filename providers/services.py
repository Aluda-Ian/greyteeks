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


def send_africas_talking_sms(provider_instance, recipients, message):
    """Send bulk SMS with Africa's Talking REST API."""
    if not recipients:
        print("Africa's Talking SMS Error: no recipients provided")
        return False

    url = 'https://api.africastalking.com/version1/messaging'
    headers = {
        'apiKey': provider_instance.api_key,
        'Accept': 'application/json',
    }
    payload = {
        'username': provider_instance.username,
        'to': ','.join(recipients),
        'message': message,
    }
    if getattr(provider_instance, 'sender_id', None):
        payload['from'] = provider_instance.sender_id

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        data = response.json()
        recipients_data = data.get('SMSMessageData', {}).get('Recipients', [])
        failed = [item for item in recipients_data if item.get('status') not in ('Success', 'success')]
        print(f"Africa's Talking response: {response.status_code} — {len(recipients_data)} recipients, {len(failed)} failed")
        return response.status_code in (200, 201) and len(failed) == 0
    except Exception as e:
        print(f"Africa's Talking SMS Exception: {e}")
        return False


def send_infobip_message(provider_instance, channel, recipients, message):
    """Send a message through Infobip REST API for SMS or WhatsApp."""
    if not recipients:
        print("Infobip Message Error: no recipients provided")
        return False

    api_key = provider_instance.api_key
    base_url = provider_instance.username
    headers = {
        'Authorization': f'App {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    if channel == 'whatsapp':
        url = f'https://{base_url}/whatsapp/1/message/text'
        payload = {
            'from': provider_instance.infobip_sender,
            'to': recipients[0],
            'content': {'text': message},
        }
    else:
        url = f'https://{base_url}/sms/2/text/advanced'
        payload = {
            'messages': [{
                'from': provider_instance.sender_id or 'Greyteeks',
                'destinations': [{'to': number} for number in recipients],
                'text': message,
            }]
        }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        if response.status_code in (200, 201):
            return True
        print(f"Infobip message error: {response.status_code} - {data}")
        return False
    except Exception as e:
        print(f"Infobip message exception: {e}")
        return False


def send_meta_whatsapp(provider_instance, recipients, template_name):
    """Send WhatsApp template messages using Meta Cloud API."""
    if not recipients:
        return False, 'No WhatsApp recipients provided.'
    if not provider_instance.access_token:
        return False, 'Missing Meta access token.'
    if not provider_instance.phone_number_id:
        return False, 'Missing Meta phone number ID.'

    url = f"https://graph.facebook.com/v17.0/{provider_instance.phone_number_id}/messages"
    headers = {
        'Authorization': f'Bearer {provider_instance.access_token}',
        'Content-Type': 'application/json',
    }

    failures = []
    for recipient in recipients:
        data = {
            'messaging_product': 'whatsapp',
            'to': recipient,
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {'code': 'en_US'},
            },
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code not in (200, 201):
                failures.append(f"{recipient}: {response.status_code} {response.text}")
        except Exception as e:
            failures.append(f"{recipient}: {e}")

    if failures:
        message = f"Meta WhatsApp failures: {'; '.join(failures)}"
        print(message)
        return False, message
    return True, 'WhatsApp template messages queued successfully.'


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
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return True, 'Meta Cloud API message sent successfully.'
        message = f'Meta Cloud API error {response.status_code}: {response.text}'
        print(message)
        return False, message
    except Exception as e:
        message = f'WhatsApp Error: {e}'
        print(message)
        return False, message


def test_whatsapp_meta_connection(provider_instance):
    """Test Meta Cloud API credentials and phone number ID."""
    if not provider_instance.access_token:
        return False, 'Access token is missing.'
    if not provider_instance.phone_number_id:
        return False, 'Phone Number ID is missing.'

    url = f"https://graph.facebook.com/v17.0/{provider_instance.phone_number_id}"
    headers = {
        "Authorization": f"Bearer {provider_instance.access_token}",
    }
    params = {
        "fields": "id,whatsapp_business_account",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            return True, 'Meta Cloud API connection verified.'
        return False, f'{response.status_code}: {response.text}'
    except Exception as e:
        print(f"WhatsApp test connection error: {e}")
        return False, str(e)


def test_whatsapp_infobip_connection(provider_instance):
    """Test Infobip WhatsApp credentials."""
    if not provider_instance.access_token:
        return False, 'Access token is missing.'
    if not provider_instance.infobip_base_url:
        return False, 'Infobip Base URL is missing.'

    # Use templates endpoint to verify API key and base URL access.
    url = f"https://{provider_instance.infobip_base_url}/whatsapp/1/templates"
    headers = {
        "Authorization": f"App {provider_instance.access_token}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        # 200 means success. Even if templates are empty, auth is correct.
        if response.status_code == 200:
            return True, 'Infobip WhatsApp connection verified.'
        return False, f'{response.status_code}: {response.text}'
    except Exception as e:
        print(f"Infobip WhatsApp test connection error: {e}")
        return False, str(e)


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
        message = f"Infobip WhatsApp Response: {response.status_code} — {response.text[:200]}"
        print(message)
        if response.status_code in (200, 201):
            return True, 'Infobip WhatsApp message sent successfully.'
        return False, message
    except Exception as e:
        message = f"Infobip WhatsApp Error: {e}"
        print(message)
        return False, message


def route_sms(provider_instance, phone_numbers, message):
    """Route SMS sending to the correct provider service based on provider type."""
    if not provider_instance:
        print("SMS Error: missing provider instance")
        return False
    name = provider_instance.name
    if name == 'africas_talking':
        return send_africas_talking_sms(provider_instance, phone_numbers, message)
    elif name == 'twilio':
        return send_bulk_twilio_sms(provider_instance, phone_numbers, message)
    elif name == 'infobip':
        return send_bulk_infobip_sms(provider_instance, phone_numbers, message)
    else:
        print(f"Unknown SMS provider: {name}")
        return False


def route_whatsapp(provider_instance, destination_phone, message_text, template_name=None):
    """Route WhatsApp sending to the correct provider service."""
    if not provider_instance:
        message = "WhatsApp Error: missing provider instance"
        print(message)
        return False, message
    provider_type = getattr(provider_instance, 'provider_type', 'meta')
    if provider_type == 'infobip':
        return send_whatsapp_infobip_message(provider_instance, destination_phone, message_text)
    if template_name:
        return send_meta_whatsapp(provider_instance, [destination_phone], template_name)
    return send_whatsapp_meta_message(provider_instance, destination_phone, message_text)


def send_custom_email(provider_instance, subject, message, recipient_list, from_email=None, html_message=False):
    """Sends email using the configured SMTP provider via Django EmailBackend."""
    if not recipient_list:
        msg = "Email Error: no recipients provided"
        print(msg)
        return False, msg

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
    if html_message:
        email.content_subtype = 'html'
    if html_message:
        email.content_subtype = 'html'

    try:
        email.send(fail_silently=False)
        connection.close()
        msg = f"Email sent to {len(recipient_list)} recipients via {provider_instance.name}"
        print(msg)
        return True, msg
    except Exception as e:
        msg = f"Email Error: {e}"
        print(msg)
        connection.close()
        return False, msg


def send_bulk_email(provider_instance, subject, body, recipients, from_email=None):
    return send_custom_email(provider_instance, subject, body, recipients, from_email=from_email)