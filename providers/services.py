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