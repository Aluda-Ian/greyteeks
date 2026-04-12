import base64
from datetime import datetime

import requests
from django.conf import settings

from accounts.models import UserQuota
from .models import PaymentGatewayConfig, PaymentTransaction


def get_mpesa_access_token(config):
    url = (
        'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        if config.is_sandbox else
        'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    )
    response = requests.get(url, auth=(config.mpesa_consumer_key, config.mpesa_consumer_secret))
    return response.json().get('access_token')


def initiate_mpesa_stk_push(transaction, config):
    token = get_mpesa_access_token(config)
    if not token:
        return False, 'Unable to fetch M-Pesa access token'

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password_str = f"{config.mpesa_shortcode}{config.mpesa_passkey}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode()

    url = (
        'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
        if config.is_sandbox else
        'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    )
    payload = {
        'BusinessShortCode': config.mpesa_shortcode,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': int(transaction.amount),
        'PartyA': transaction.phone_number,
        'PartyB': config.mpesa_shortcode,
        'PhoneNumber': transaction.phone_number,
        'CallBackURL': config.mpesa_callback_url,
        'AccountReference': f'Greyteeks-{transaction.id}',
        'TransactionDesc': f'Quota top-up {transaction.plan.name}',
    }
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        if data.get('ResponseCode') == '0':
            return True, data.get('CheckoutRequestID')
        return False, data.get('errorMessage', data.get('errorMessage', 'STK push failed'))
    except Exception as e:
        return False, str(e)


def verify_mpesa_transaction(checkout_request_id, config):
    token = get_mpesa_access_token(config)
    if not token:
        return False, 'Unable to fetch M-Pesa access token'

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password_str = f"{config.mpesa_shortcode}{config.mpesa_passkey}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode()

    url = (
        'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query'
        if config.is_sandbox else
        'https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query'
    )
    payload = {
        'BusinessShortCode': config.mpesa_shortcode,
        'Password': password,
        'Timestamp': timestamp,
        'CheckoutRequestID': checkout_request_id,
    }
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        if data.get('ResultCode') == 0 or data.get('ResultCode') == '0':
            return True, data.get('MpesaReceiptNumber', '')
        return False, data.get('ResultDesc', 'Payment not completed')
    except Exception as e:
        return False, str(e)


def initiate_paystack_payment(transaction, config):
    url = 'https://api.paystack.co/transaction/initialize'
    headers = {
        'Authorization': f'Bearer {config.paystack_secret_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'email': transaction.user.email,
        'amount': int(transaction.amount * 100),
        'currency': transaction.currency,
        'reference': transaction.paystack_reference,
        'callback_url': f'{settings.SITE_URL}/billing/paystack/callback/',
        'metadata': {
            'transaction_id': transaction.id,
            'plan_name': transaction.plan.name,
            'units': transaction.units_purchased,
        },
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        if data.get('status'):
            return True, data['data']['authorization_url']
        return False, data.get('message', 'Paystack initialization failed')
    except Exception as e:
        return False, str(e)


def verify_paystack_payment(reference, config):
    url = f'https://api.paystack.co/transaction/verify/{reference}'
    headers = {'Authorization': f'Bearer {config.paystack_secret_key}'}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        if data.get('status') and data['data']['status'] == 'success':
            return True, data['data']
        return False, data.get('message', 'Payment verification failed')
    except Exception as e:
        return False, str(e)


def get_paypal_access_token(config):
    url = (
        'https://api-m.sandbox.paypal.com/v1/oauth2/token'
        if config.is_sandbox else
        'https://api-m.paypal.com/v1/oauth2/token'
    )
    response = requests.post(
        url,
        data={'grant_type': 'client_credentials'},
        auth=(config.paypal_client_id, config.paypal_client_secret),
        timeout=30,
    )
    return response.json().get('access_token')


def create_paypal_order(transaction, config):
    token = get_paypal_access_token(config)
    if not token:
        return False, 'Unable to fetch PayPal access token', None

    url = (
        'https://api-m.sandbox.paypal.com/v2/checkout/orders'
        if config.is_sandbox else
        'https://api-m.paypal.com/v2/checkout/orders'
    )
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'amount': {
                'currency_code': 'USD',
                'value': str(transaction.amount),
            },
            'description': f'Greyteeks {transaction.plan.name} — {transaction.units_purchased} units',
            'reference_id': str(transaction.id),
        }],
        'application_context': {
            'return_url': f'{settings.SITE_URL}/billing/paypal/success/',
            'cancel_url': f'{settings.SITE_URL}/billing/paypal/cancel/',
        },
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        if data.get('id'):
            approve_url = next(
                (link['href'] for link in data.get('links', []) if link.get('rel') == 'approve'),
                None,
            )
            return True, data['id'], approve_url
        return False, data.get('message', 'PayPal order creation failed'), None
    except Exception as e:
        return False, str(e), None


def capture_paypal_order(order_id, config):
    token = get_paypal_access_token(config)
    if not token:
        return False, 'Unable to fetch PayPal access token'

    url = (
        f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture'
        if config.is_sandbox else
        f'https://api-m.paypal.com/v2/checkout/orders/{order_id}/capture'
    )
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    try:
        response = requests.post(url, headers=headers, timeout=30)
        data = response.json()
        if data.get('status') == 'COMPLETED':
            return True, data
        return False, data.get('message', 'PayPal capture failed')
    except Exception as e:
        return False, str(e)


def credit_user_quota(transaction):
    quota, _ = UserQuota.objects.get_or_create(user=transaction.user)
    quota.max_units += transaction.units_purchased
    quota.save()
    transaction.status = 'success'
    transaction.save()
