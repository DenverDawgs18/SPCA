from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def ensure_staff_has_volunteer_profile(sender, instance, **kwargs):
    """Any staff/superuser automatically gets a Volunteer profile."""
    if instance.is_staff or instance.is_superuser:
        from .models import Volunteer
        Volunteer.objects.get_or_create(user=instance)
