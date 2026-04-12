from django.conf import settings
from django.db import models


class PaymentGatewayConfig(models.Model):
    """Admin-configured API keys for each payment gateway."""
    GATEWAY_CHOICES = [
        ('mpesa', 'M-Pesa Daraja'),
        ('paystack', 'Paystack'),
        ('paypal', 'PayPal'),
    ]
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, unique=True)
    is_active = models.BooleanField(default=False)
    is_sandbox = models.BooleanField(default=True, help_text="Use sandbox/test credentials")

    # M-Pesa fields
    mpesa_consumer_key = models.CharField(max_length=255, blank=True)
    mpesa_consumer_secret = models.CharField(max_length=255, blank=True)
    mpesa_shortcode = models.CharField(max_length=20, blank=True)
    mpesa_passkey = models.CharField(max_length=255, blank=True)
    mpesa_callback_url = models.URLField(blank=True)

    # Paystack fields
    paystack_public_key = models.CharField(max_length=255, blank=True)
    paystack_secret_key = models.CharField(max_length=255, blank=True)

    # PayPal fields
    paypal_client_id = models.CharField(max_length=255, blank=True)
    paypal_client_secret = models.CharField(max_length=255, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_gateway_display()} ({'Sandbox' if self.is_sandbox else 'Live'})"


class PricingPlan(models.Model):
    """Plans customers can purchase to top up their quota."""
    name = models.CharField(max_length=100)
    units = models.PositiveIntegerField(help_text="Number of message units this plan adds")
    price_kes = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in KES for M-Pesa")
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in USD for PayPal/Paystack")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — {self.units} units"


class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    GATEWAY_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('paystack', 'Paystack'),
        ('paypal', 'PayPal'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    plan = models.ForeignKey(PricingPlan, on_delete=models.SET_NULL, null=True)
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='KES')
    units_purchased = models.PositiveIntegerField(default=0)

    gateway_reference = models.CharField(max_length=255, blank=True, help_text="Gateway transaction ID")
    mpesa_checkout_request_id = models.CharField(max_length=255, blank=True)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True)
    paystack_reference = models.CharField(max_length=255, blank=True)
    paypal_order_id = models.CharField(max_length=255, blank=True)

    phone_number = models.CharField(max_length=20, blank=True, help_text="For M-Pesa STK push")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — {self.gateway} — {self.status} — {self.units_purchased} units"
