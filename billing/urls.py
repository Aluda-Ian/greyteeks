from django.urls import path

from . import views

urlpatterns = [
    path('', views.billing_home, name='billing_home'),
    path('pay/', views.initiate_payment, name='initiate_payment'),
    path('mpesa/status/<int:transaction_id>/', views.check_mpesa_status, name='check_mpesa_status'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('paystack/callback/', views.paystack_callback, name='paystack_callback'),
    path('paypal/success/', views.paypal_success, name='paypal_success'),
    path('paypal/cancel/', views.paypal_cancel, name='paypal_cancel'),
    path('admin/settings/', views.admin_billing_settings, name='admin_billing_settings'),
    path('admin/transactions/', views.admin_transactions, name='admin_transactions'),
    path('admin/plans/', views.admin_plans, name='admin_plans'),
]
