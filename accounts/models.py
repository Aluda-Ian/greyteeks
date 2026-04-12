from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserQuota(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quota')
    max_units = models.PositiveIntegerField(default=100)
    units_used = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} quota: {self.units_used}/{self.max_units}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_quota(sender, instance, created, **kwargs):
    if created:
        UserQuota.objects.create(user=instance)
