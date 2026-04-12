import africastalking
import requests
import smtplib
from email.message import EmailMessage
from django.conf import settings

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


def send_bulk_email(provider_instance, subject, body, recipients, from_email=None):
    """Sends bulk email using the configured SMTP provider."""
    if not recipients:
        print("Email Error: no recipients provided")
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email or provider_instance.from_email
    msg['To'] = ', '.join(recipients)
    msg.set_content(body)

    try:
        if provider_instance.use_ssl:
            server = smtplib.SMTP_SSL(provider_instance.host, provider_instance.port, timeout=20)
        else:
            server = smtplib.SMTP(provider_instance.host, provider_instance.port, timeout=20)
            if provider_instance.use_tls:
                server.starttls()

        server.login(provider_instance.username, provider_instance.password)
        server.send_message(msg)
        server.quit()
        print(f"Bulk email sent to {len(recipients)} recipients")
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False