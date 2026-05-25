from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class SiteSettings(models.Model):
    """Single-row table for admin-configurable thresholds."""
    inactivity_days = models.IntegerField(
        default=90,
        help_text="Look-back window in days for inactivity check.",
    )
    inactivity_min_visits = models.IntegerField(
        default=2,
        help_text="Minimum number of visits within the window to be considered active.",
    )

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return f"Settings: ≥{self.inactivity_min_visits} visits / {self.inactivity_days} days"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


SHIRT_SIZES = [("XS", "XS"), ("S", "S"), ("M", "M"), ("L", "L"), ("XL", "XL"), ("XXL", "XXL")]

AVAILABILITY_OPTIONS = [
    ("mon_am", "Monday morning"),
    ("mon_pm", "Monday afternoon"),
    ("tue_am", "Tuesday morning"),
    ("tue_pm", "Tuesday afternoon"),
    ("wed_am", "Wednesday morning"),
    ("wed_pm", "Wednesday afternoon"),
    ("thu_am", "Thursday morning"),
    ("thu_pm", "Thursday afternoon"),
    ("fri_am", "Friday morning"),
    ("fri_pm", "Friday afternoon"),
    ("sat_am", "Saturday morning"),
    ("sat_pm", "Saturday afternoon"),
    ("sun_am", "Sunday morning"),
    ("sun_pm", "Sunday afternoon"),
]

ACTIVITY_CHOICES = [
    ("dog_walking", "Dog Walking"),
    ("cat_socialization", "Cat Socialization"),
    ("cleaning", "Cleaning & Maintenance"),
    ("admin", "Administrative Support"),
    ("adoption_counseling", "Adoption Counseling"),
    ("fundraising", "Fundraising / Events"),
    ("transport", "Animal Transport"),
    ("other", "Other"),
]


class Volunteer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="volunteer_profile")
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    # Stored as a comma-separated list of availability keys
    availability = models.JSONField(default=list)
    skills = models.TextField(blank=True, help_text="Special skills or experience (e.g. vet tech, dog trainer)")
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=20)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    t_shirt_size = models.CharField(max_length=4, choices=SHIRT_SIZES, blank=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_volunteers"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Internal manager notes — not visible to the volunteer.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def visit_count_in_window(self):
        settings = SiteSettings.get()
        cutoff = timezone.now().date() - timedelta(days=settings.inactivity_days)
        return self.visits.filter(visit_date__gte=cutoff).count()

    def is_active(self):
        settings = SiteSettings.get()
        return self.visit_count_in_window() >= settings.inactivity_min_visits

    def last_visit(self):
        return self.visits.order_by("-visit_date").first()

    def total_hours(self):
        from django.db.models import Sum
        result = self.visits.aggregate(total=Sum("hours"))["total"]
        return result or 0

    def availability_display(self):
        mapping = dict(AVAILABILITY_OPTIONS)
        return [mapping[k] for k in self.availability if k in mapping]


class VolunteerVisit(models.Model):
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, related_name="visits")
    visit_date = models.DateField()
    hours = models.DecimalField(max_digits=4, decimal_places=1)
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_CHOICES, default="other")
    notes = models.TextField(blank=True)
    logged_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="logged_visits"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-visit_date", "-created_at"]

    def __str__(self):
        return f"{self.volunteer} — {self.visit_date} ({self.hours}h)"
