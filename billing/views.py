import json
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from .models import PaymentGatewayConfig, PaymentTransaction, PricingPlan
from .services import (
    capture_paypal_order,
    credit_user_quota,
    create_paypal_order,
    initiate_mpesa_stk_push,
    initiate_paystack_payment,
    verify_mpesa_transaction,
    verify_paystack_payment,
)


@login_required
def billing_home(request):
    plans = PricingPlan.objects.filter(is_active=True).order_by('price_kes')
    gateways = PaymentGatewayConfig.objects.filter(is_active=True).order_by('gateway')
    user_quota = getattr(request.user, 'quota', None)
    if user_quota is None:
        from accounts.models import UserQuota

        user_quota, _ = UserQuota.objects.get_or_create(user=request.user)
    transactions = PaymentTransaction.objects.filter(user=request.user).order_by('-created_at')[:10]

    used_units = user_quota.units_used or 0
    max_units = user_quota.max_units or 0
    quota_percent = 0
    if max_units > 0:
        quota_percent = min(100, int(round((used_units / max_units) * 100)))

    context = {
        'plans': plans,
        'gateways': gateways,
        'user_quota': user_quota,
        'transactions': transactions,
        'quota_percent': quota_percent,
    }
    return render(request, 'billing/billing_home.html', context)


@login_required
def initiate_payment(request):
    if request.method != 'POST':
        return redirect('billing_home')

    plan_id = request.POST.get('plan_id')
    gateway = request.POST.get('gateway')
    phone_number = request.POST.get('phone_number', '').strip()
    plan = get_object_or_404(PricingPlan, id=plan_id, is_active=True)
    config = PaymentGatewayConfig.objects.filter(gateway=gateway, is_active=True).first()

    if not config:
        messages.error(request, 'Selected payment gateway is not available.')
        return redirect('billing_home')

    if gateway == 'mpesa' and not phone_number:
        return JsonResponse({'status': 'failed', 'message': 'Phone number is required for M-Pesa.'}, status=400)

    if gateway == 'mpesa':
        amount = plan.price_kes
        currency = 'KES'
    elif gateway == 'paystack':
        amount = plan.price_kes
        currency = 'KES'
    else:
        amount = plan.price_usd
        currency = 'USD'

    transaction = PaymentTransaction.objects.create(
        user=request.user,
        plan=plan,
        gateway=gateway,
        status='pending',
        amount=amount,
        currency=currency,
        units_purchased=plan.units,
        phone_number=phone_number if gateway == 'mpesa' else '',
    )

    if gateway == 'mpesa':
        success, result = initiate_mpesa_stk_push(transaction, config)
        if success:
            transaction.mpesa_checkout_request_id = result
            transaction.gateway_reference = result
            transaction.save()
            return JsonResponse({
                'status': 'pending',
                'message': 'Check your phone for the M-Pesa prompt.',
                'transaction_id': transaction.id,
            })
        transaction.status = 'failed'
        transaction.save()
        return JsonResponse({'status': 'failed', 'message': result}, status=400)

    if gateway == 'paystack':
        reference = f'greyteeks-{transaction.id}-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        transaction.paystack_reference = reference
        transaction.gateway_reference = reference
        transaction.save()
        success, result = initiate_paystack_payment(transaction, config)
        if success:
            return redirect(result)
        transaction.status = 'failed'
        transaction.save()
        print(f"[Paystack] Payment initiation failed for transaction {transaction.id}: {result}")
        messages.error(request, f'Paystack error: {result}. Please check your Paystack sandbox keys and try again.')
        return redirect('billing_home')

    if gateway == 'paypal':
        success, order_id, approve_url = create_paypal_order(transaction, config)
        if success and approve_url:
            transaction.paypal_order_id = order_id
            transaction.gateway_reference = order_id
            transaction.save()
            return redirect(approve_url)
        transaction.status = 'failed'
        transaction.save()
        messages.error(request, order_id)
        return redirect('billing_home')

    messages.error(request, 'Unsupported payment method.')
    transaction.status = 'failed'
    transaction.save()
    return redirect('billing_home')


@login_required
def check_mpesa_status(request, transaction_id):
    transaction = get_object_or_404(PaymentTransaction, id=transaction_id, user=request.user)
    if transaction.gateway != 'mpesa' or not transaction.mpesa_checkout_request_id:
        return JsonResponse({'status': 'failed', 'message': 'Invalid M-Pesa transaction.'}, status=400)

    config = PaymentGatewayConfig.objects.filter(gateway='mpesa', is_active=True).first()
    if not config:
        return JsonResponse({'status': 'failed', 'message': 'M-Pesa is not configured.'}, status=400)

    success, result = verify_mpesa_transaction(transaction.mpesa_checkout_request_id, config)
    if success:
        if transaction.status != 'success':
            transaction.mpesa_receipt_number = result
            credit_user_quota(transaction)
        return JsonResponse({'status': 'success', 'units': transaction.units_purchased})

    if 'pending' in result.lower() or 'not completed' in result.lower():
        return JsonResponse({'status': 'pending'})

    transaction.status = 'failed'
    transaction.save()
    return JsonResponse({'status': 'failed', 'message': result}, status=400)


@csrf_exempt
def mpesa_callback(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except ValueError:
        return HttpResponse('OK')

    callback = payload.get('Body', {}).get('stkCallback') if isinstance(payload, dict) else None
    if not callback:
        callback = payload.get('stkCallback') if isinstance(payload, dict) else None

    if not callback:
        return HttpResponse('OK')

    checkout_id = callback.get('CheckoutRequestID')
    account_ref = callback.get('AccountReference')
    result_code = callback.get('ResultCode')
    receipt_number = ''
    metadata = callback.get('CallbackMetadata', {}).get('Item', [])
    for item in metadata:
        if item.get('Name') == 'MpesaReceiptNumber':
            receipt_number = item.get('Value')

    transaction = None
    if checkout_id:
        transaction = PaymentTransaction.objects.filter(mpesa_checkout_request_id=checkout_id).first()
    if not transaction and account_ref:
        transaction = PaymentTransaction.objects.filter(gateway_reference=account_ref).first()
    if not transaction:
        return HttpResponse('OK')

    if result_code == 0 or result_code == '0':
        transaction.mpesa_receipt_number = receipt_number or transaction.mpesa_receipt_number
        if transaction.status != 'success':
            credit_user_quota(transaction)
        return HttpResponse('OK')

    transaction.status = 'failed'
    transaction.save()
    return HttpResponse('OK')


@login_required
def paystack_callback(request):
    reference = request.GET.get('reference')
    if not reference:
        messages.error(request, 'Missing Paystack reference.')
        return redirect('billing_home')

    transaction = PaymentTransaction.objects.filter(paystack_reference=reference, user=request.user).first()
    if not transaction:
        messages.error(request, 'Paystack transaction not found.')
        return redirect('billing_home')

    config = PaymentGatewayConfig.objects.filter(gateway='paystack', is_active=True).first()
    if not config:
        messages.error(request, 'Paystack is not configured.')
        return redirect('billing_home')

    success, data = verify_paystack_payment(reference, config)
    if success:
        if transaction.status != 'success':
            transaction.gateway_reference = data.get('reference', reference)
            transaction.save()
            credit_user_quota(transaction)
        messages.success(request, 'Paystack payment completed successfully.')
        return redirect('billing_home')

    transaction.status = 'failed'
    transaction.save()
    messages.error(request, f'Paystack verification failed: {data}')
    return redirect('billing_home')


@login_required
def paypal_success(request):
    order_id = request.GET.get('token')
    if not order_id:
        messages.error(request, 'PayPal order token is missing.')
        return redirect('billing_home')

    transaction = PaymentTransaction.objects.filter(paypal_order_id=order_id, user=request.user).first()
    if not transaction:
        messages.error(request, 'PayPal transaction not found.')
        return redirect('billing_home')

    config = PaymentGatewayConfig.objects.filter(gateway='paypal', is_active=True).first()
    if not config:
        messages.error(request, 'PayPal is not configured.')
        return redirect('billing_home')

    success, result = capture_paypal_order(order_id, config)
    if success:
        if transaction.status != 'success':
            transaction.gateway_reference = order_id
            transaction.save()
            credit_user_quota(transaction)
        messages.success(request, 'PayPal payment completed successfully.')
        return redirect('billing_home')

    transaction.status = 'failed'
    transaction.save()
    messages.error(request, f'PayPal capture failed: {result}')
    return redirect('billing_home')


@login_required
def paypal_cancel(request):
    order_id = request.GET.get('token')
    transaction = PaymentTransaction.objects.filter(paypal_order_id=order_id, user=request.user).first()
    if transaction:
        transaction.status = 'cancelled'
        transaction.save()
    messages.info(request, 'PayPal payment was cancelled.')
    return redirect('billing_home')


def _require_staff(request):
    if not request.user.is_staff:
        raise PermissionDenied


@login_required
def admin_billing_settings(request):
    _require_staff(request)
    mpesa_config, _ = PaymentGatewayConfig.objects.get_or_create(gateway='mpesa')
    paystack_config, _ = PaymentGatewayConfig.objects.get_or_create(gateway='paystack')
    paypal_config, _ = PaymentGatewayConfig.objects.get_or_create(gateway='paypal')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_mpesa':
            mpesa_config.mpesa_consumer_key = request.POST.get('mpesa_consumer_key', '')
            mpesa_config.mpesa_consumer_secret = request.POST.get('mpesa_consumer_secret', '')
            mpesa_config.mpesa_shortcode = request.POST.get('mpesa_shortcode', '')
            mpesa_config.mpesa_passkey = request.POST.get('mpesa_passkey', '')
            mpesa_config.mpesa_callback_url = request.POST.get('mpesa_callback_url', '')
            mpesa_config.is_sandbox = request.POST.get('mpesa_is_sandbox') == 'on'
            mpesa_config.save()
            messages.success(request, 'M-Pesa configuration saved.')
        elif action == 'toggle_mpesa':
            mpesa_config.is_active = not mpesa_config.is_active
            mpesa_config.save()
            messages.success(request, 'M-Pesa activation toggled.')
        elif action == 'save_paystack':
            paystack_config.paystack_public_key = request.POST.get('paystack_public_key', '')
            paystack_config.paystack_secret_key = request.POST.get('paystack_secret_key', '')
            paystack_config.is_sandbox = request.POST.get('paystack_is_sandbox') == 'on'
            paystack_config.save()
            messages.success(request, 'Paystack configuration saved.')
        elif action == 'toggle_paystack':
            paystack_config.is_active = not paystack_config.is_active
            paystack_config.save()
            messages.success(request, 'Paystack activation toggled.')
        elif action == 'save_paypal':
            paypal_config.paypal_client_id = request.POST.get('paypal_client_id', '')
            paypal_config.paypal_client_secret = request.POST.get('paypal_client_secret', '')
            paypal_config.is_sandbox = request.POST.get('paypal_is_sandbox') == 'on'
            paypal_config.save()
            messages.success(request, 'PayPal configuration saved.')
        elif action == 'toggle_paypal':
            paypal_config.is_active = not paypal_config.is_active
            paypal_config.save()
            messages.success(request, 'PayPal activation toggled.')
        return redirect('admin_billing_settings')

    context = {
        'mpesa_config': mpesa_config,
        'paystack_config': paystack_config,
        'paypal_config': paypal_config,
    }
    return render(request, 'billing/admin_settings.html', context)


@login_required
def admin_transactions(request):
    _require_staff(request)
    status_filter = request.GET.get('status')
    transactions = PaymentTransaction.objects.select_related('user', 'plan').order_by('-created_at')
    if status_filter in ['pending', 'success', 'failed', 'cancelled']:
        transactions = transactions.filter(status=status_filter)
    context = {
        'transactions': transactions,
        'status_filter': status_filter or 'all',
    }
    return render(request, 'billing/admin_transactions.html', context)


@login_required
def admin_plans(request):
    _require_staff(request)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_plan':
            PricingPlan.objects.create(
                name=request.POST.get('name', '').strip(),
                units=int(request.POST.get('units') or 0),
                price_kes=request.POST.get('price_kes') or 0,
                price_usd=request.POST.get('price_usd') or 0,
                is_featured=request.POST.get('is_featured') == 'on',
            )
            messages.success(request, 'Pricing plan created.')
        elif action == 'toggle_plan':
            plan = get_object_or_404(PricingPlan, id=request.POST.get('plan_id'))
            plan.is_active = not plan.is_active
            plan.save()
            messages.success(request, 'Pricing plan status updated.')
        elif action == 'delete_plan':
            plan = get_object_or_404(PricingPlan, id=request.POST.get('plan_id'))
            plan.delete()
            messages.success(request, 'Pricing plan deleted.')
        return redirect('admin_plans')

    plans = PricingPlan.objects.order_by('price_kes')
    return render(request, 'billing/admin_plans.html', {'plans': plans})
