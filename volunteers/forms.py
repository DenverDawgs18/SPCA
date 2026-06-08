from django import forms
from django.utils import timezone

from .models import (
    VolunteerApplication, Volunteer, Shift, HourLog,
    AVAILABILITY_OPTIONS, SHIRT_SIZES, ACTIVITY_CHOICES,
)


# ---------------------------------------------------------------------------
# Application form (public)
# ---------------------------------------------------------------------------

class ApplicationForm(forms.ModelForm):
    availability = forms.MultipleChoiceField(
        choices=AVAILABILITY_OPTIONS,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Availability",
    )

    class Meta:
        model = VolunteerApplication
        fields = [
            "first_name", "last_name", "email", "phone",
            "address", "city", "state", "zip_code", "date_of_birth",
            "why_volunteer", "animal_experience", "skills", "availability",
            "emergency_contact_name", "emergency_contact_phone", "emergency_contact_relationship",
            "t_shirt_size", "is_over_18", "agrees_to_background_check",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "why_volunteer": forms.Textarea(attrs={"rows": 4}),
            "animal_experience": forms.Textarea(attrs={"rows": 4}),
            "skills": forms.Textarea(attrs={"rows": 3}),
            "is_over_18": forms.CheckboxInput(),
            "agrees_to_background_check": forms.CheckboxInput(),
        }
        labels = {
            "is_over_18": "I confirm I am 18 years of age or older",
            "agrees_to_background_check": "I agree to a background check as part of the volunteer process",
        }

    def clean_is_over_18(self):
        value = self.cleaned_data.get("is_over_18")
        if not value:
            raise forms.ValidationError("You must be 18 or older to volunteer.")
        return value

    def clean_agrees_to_background_check(self):
        value = self.cleaned_data.get("agrees_to_background_check")
        if not value:
            raise forms.ValidationError("You must agree to a background check to proceed.")
        return value


# ---------------------------------------------------------------------------
# Kiosk hour log form (no login required)
# ---------------------------------------------------------------------------

class HourLogKioskForm(forms.Form):
    volunteer = forms.ModelChoiceField(
        queryset=Volunteer.objects.filter(is_active=True).select_related("user").order_by(
            "user__last_name", "user__first_name"
        ),
        empty_label="— Select your name —",
        label="Your Name",
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "js-today"}),
        initial=timezone.now,
        label="Date",
    )
    hours = forms.DecimalField(
        max_digits=4,
        decimal_places=1,
        min_value=0.5,
        max_value=24,
        label="Hours",
    )
    activity_type = forms.ChoiceField(
        choices=ACTIVITY_CHOICES,
        label="Activity Type",
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="Notes (optional)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["volunteer"].label_from_instance = lambda obj: obj.full_name

    def clean_date(self):
        d = self.cleaned_data.get("date")
        if d and d > timezone.now().date():
            raise forms.ValidationError("Date cannot be in the future.")
        return d


# ---------------------------------------------------------------------------
# Shift form (admin)
# ---------------------------------------------------------------------------

class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ["title", "description", "date", "start_time", "end_time",
                  "activity_type", "capacity"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if start and end and end <= start:
            self.add_error("end_time", "End time must be after start time.")
        return cleaned


# ---------------------------------------------------------------------------
# Group email form (manager)
# ---------------------------------------------------------------------------

RECIPIENT_CHOICES = [
    ("all", "All volunteers"),
    ("active", "Active volunteers only"),
    ("inactive", "Inactive volunteers only"),
]


class GroupEmailForm(forms.Form):
    subject = forms.CharField(max_length=200, label="Subject")
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 10}), label="Message")
    recipient_filter = forms.ChoiceField(choices=RECIPIENT_CHOICES, label="Send to")


# ---------------------------------------------------------------------------
# Deny application form
# ---------------------------------------------------------------------------

class DenyForm(forms.Form):
    denial_reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Reason for denial (will be emailed to the applicant)",
    )


# ---------------------------------------------------------------------------
# Manager notes form
# ---------------------------------------------------------------------------

class ManagerNotesForm(forms.ModelForm):
    class Meta:
        model = Volunteer
        fields = ["notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 5})}


# ---------------------------------------------------------------------------
# Site settings form
# ---------------------------------------------------------------------------

class SiteSettingsForm(forms.Form):
    inactivity_days = forms.IntegerField(
        min_value=1,
        label="Inactivity window (days)",
        help_text="Number of days to look back when checking activity.",
    )
    inactivity_min_visits = forms.IntegerField(
        min_value=1,
        label="Minimum logs in window",
        help_text="Number of hour logs required within the window to be considered active.",
    )
