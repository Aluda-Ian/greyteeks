from django.urls import path

from .views import api_generate_copy, api_suggest_reply

urlpatterns = [
    path('generate-copy/', api_generate_copy, name='api_generate_copy'),
    path('suggest-reply/<int:conversation_id>/', api_suggest_reply, name='api_suggest_reply'),
]
