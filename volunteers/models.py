from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


# ---------------------------------------------------------------------------
# Shared choices
# ---------------------------------------------------------------------------

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

APPLICATION_STATUS = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("denied", "Denied"),
]


# ---------------------------------------------------------------------------
# SiteSettings — singleton
# ---------------------------------------------------------------------------

class SiteSettings(models.Model):
    inactivity_days = models.IntegerField(
        default=90,
        help_text="Look-back window in days for inactivity check.",
    )
    inactivity_min_visits = models.IntegerField(
        default=2,
        help_text="Minimum visits within the window to be considered active.",
    )
    notification_from_email = models.EmailField(
        blank=True,
        help_text="From address for notification emails (leave blank to use DEFAULT_FROM_EMAIL).",
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


# ---------------------------------------------------------------------------
# VolunteerApplication
# ---------------------------------------------------------------------------

class VolunteerApplication(models.Model):
    # Personal info
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, default="OH")
    zip_code = models.CharField(max_length=10)
    date_of_birth = models.DateField()

    # Application questions
    why_volunteer = models.TextField()
    animal_experience = models.TextField()
    skills = models.TextField(blank=True)
    availability = models.JSONField(default=list)

    # Emergency contact
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=20)
    emergency_contact_relationship = models.CharField(max_length=50)

    # Additional
    t_shirt_size = models.CharField(max_length=4, choices=SHIRT_SIZES, blank=True)
    is_over_18 = models.BooleanField(default=False)
    agrees_to_background_check = models.BooleanField(default=False)

    # Status
    status = models.CharField(max_length=20, choices=APPLICATION_STATUS, default="pending")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_applications",
    )
    denial_reason = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="volunteer_application",
    )

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.status})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def availability_display(self):
        mapping = dict(AVAILABILITY_OPTIONS)
        return [mapping[k] for k in self.availability if k in mapping]


# ---------------------------------------------------------------------------
# AdminNotificationPreference
# ---------------------------------------------------------------------------

class AdminNotificationPreference(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    notify_new_application = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Admin Notification Preference"

    def __str__(self):
        return f"{self.user.username} — notify={self.notify_new_application}"


# ---------------------------------------------------------------------------
# Volunteer
# ---------------------------------------------------------------------------

class Volunteer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="volunteer_profile")
    application = models.OneToOneField(
        VolunteerApplication, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="volunteer_record",
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Internal manager notes — not visible to the volunteer.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def email(self):
        return self.user.email

    @property
    def phone(self):
        if self.application:
            return self.application.phone
        return ""

    @property
    def total_hours(self):
        from django.db.models import Sum
        result = self.hour_logs.aggregate(total=Sum("hours"))["total"]
        return result or 0

    @property
    def last_log_date(self):
        last = self.hour_logs.order_by("-date").first()
        return last.date if last else None

    def is_inactive(self):
        settings = SiteSettings.get()
        cutoff = timezone.now().date() - timedelta(days=settings.inactivity_days)
        count = self.hour_logs.filter(date__gte=cutoff).count()
        return count < settings.inactivity_min_visits

    def log_count_in_window(self):
        settings = SiteSettings.get()
        cutoff = timezone.now().date() - timedelta(days=settings.inactivity_days)
        return self.hour_logs.filter(date__gte=cutoff).count()


# ---------------------------------------------------------------------------
# Shift
# ---------------------------------------------------------------------------

class Shift(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_CHOICES, default="other")
    capacity = models.PositiveIntegerField(default=10)
    is_cancelled = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_shifts",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.title} — {self.date}"

    @property
    def signup_count(self):
        return self.signups.filter(is_cancelled=False).count()

    @property
    def is_full(self):
        return self.signup_count >= self.capacity

    @property
    def spots_left(self):
        return max(0, self.capacity - self.signup_count)

    @property
    def duration_hours(self):
        from datetime import datetime, date as date_type
        start = datetime.combine(date_type.today(), self.start_time)
        end = datetime.combine(date_type.today(), self.end_time)
        delta = end - start
        return round(delta.seconds / 3600, 1)


# ---------------------------------------------------------------------------
# ShiftSignup
# ---------------------------------------------------------------------------

class ShiftSignup(models.Model):
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, related_name="signups")
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="signups")
    signed_up_at = models.DateTimeField(auto_now_add=True)
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("volunteer", "shift")]
        ordering = ["-signed_up_at"]

    def __str__(self):
        return f"{self.volunteer} → {self.shift}"


# ---------------------------------------------------------------------------
# HourLog
# ---------------------------------------------------------------------------

class HourLog(models.Model):
    volunteer = models.ForeignKey(
        Volunteer, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hour_logs",
    )
    volunteer_name = models.CharField(max_length=200)
    date = models.DateField()
    hours = models.DecimalField(max_digits=4, decimal_places=1)
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_CHOICES, default="other")
    notes = models.TextField(blank=True)
    shift = models.ForeignKey(
        Shift, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hour_logs",
    )
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-logged_at"]

    def __str__(self):
        return f"{self.volunteer_name} — {self.date} ({self.hours}h)"


# ---------------------------------------------------------------------------
# GroupEmailRecord
# ---------------------------------------------------------------------------

class GroupEmailRecord(models.Model):
    subject = models.CharField(max_length=200)
    body = models.TextField()
    sent_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sent_group_emails",
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    recipient_count = models.IntegerField(default=0)
    recipient_filter = models.CharField(max_length=50, default="all")

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.subject} ({self.sent_at:%Y-%m-%d})"
