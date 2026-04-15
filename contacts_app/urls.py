from django.urls import path

from .views import manage_lead_forms, submit_lead_form

urlpatterns = [
    path('', manage_lead_forms, name='manage_lead_forms'),
    path('submit/<uuid:form_uuid>/', submit_lead_form, name='submit_lead_form'),
]
