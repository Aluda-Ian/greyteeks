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