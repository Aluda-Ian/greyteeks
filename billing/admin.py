from django.contrib import admin

from .models import PaymentGatewayConfig, PaymentTransaction, PricingPlan


@admin.register(PaymentGatewayConfig)
class PaymentGatewayConfigAdmin(admin.ModelAdmin):
    list_display = ('gateway', 'is_active', 'is_sandbox', 'updated_at')


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'units', 'price_kes', 'price_usd', 'description', 'is_active', 'is_featured')


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'gateway', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('gateway', 'status')
    search_fields = ('user__username', 'gateway_reference', 'mpesa_receipt_number')
