from django.db import models
from django.contrib.auth.models import User

class Group(models.Model):
    # This 'user' field is what the dashboard was looking for!
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_groups') 
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __clstr__(self):
        return self.name

class Contact(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='contacts')
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='conversations')
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.contact.name or self.contact.phone_number} chat"


class Message(models.Model):
    DIRECTION_CHOICES = [
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ]
    CHANNEL_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'Email'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.direction} {self.channel} message at {self.timestamp}"
