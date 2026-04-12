import africastalking
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