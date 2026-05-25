from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import Volunteer, VolunteerVisit, AVAILABILITY_OPTIONS, SHIRT_SIZES, ACTIVITY_CHOICES


class RegistrationForm(forms.Form):
    first_name = forms.CharField(max_length=50)
    last_name  = forms.CharField(max_length=50)
    email      = forms.EmailField()
    username   = forms.CharField(max_length=50)
    password   = forms.CharField(widget=forms.PasswordInput)
    password2  = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
    phone      = forms.CharField(max_length=20)
    address    = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
    availability = forms.MultipleChoiceField(
        choices=AVAILABILITY_OPTIONS,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    skills = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        help_text="Any relevant experience (e.g. dog training, vet tech, carpentry)",
    )
    emergency_contact_name  = forms.CharField(max_length=100)
    emergency_contact_phone = forms.CharField(max_length=20)
    emergency_contact_relationship = forms.CharField(max_length=50, required=False)
    t_shirt_size = forms.ChoiceField(choices=[("", "— Select —")] + list(SHIRT_SIZES), required=False)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get("password")
        pw2 = cleaned.get("password2")
        if pw1 and pw2 and pw1 != pw2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50)
    last_name  = forms.CharField(max_length=50)
    email      = forms.EmailField()
    availability = forms.MultipleChoiceField(
        choices=AVAILABILITY_OPTIONS,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model  = Volunteer
        fields = [
            "phone", "address", "availability", "skills",
            "emergency_contact_name", "emergency_contact_phone",
            "emergency_contact_relationship", "t_shirt_size",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "skills":  forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            user = self.instance.user
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial  = user.last_name
            self.fields["email"].initial      = user.email
            self.fields["availability"].initial = self.instance.availability


class LogVisitForm(forms.ModelForm):
    class Meta:
        model  = VolunteerVisit
        fields = ["visit_date", "hours", "activity_type", "notes"]
        widgets = {
            "visit_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_hours(self):
        hours = self.cleaned_data["hours"]
        if hours <= 0 or hours > 24:
            raise forms.ValidationError("Hours must be between 0.5 and 24.")
        return hours


class ManagerLogVisitForm(forms.ModelForm):
    """Like LogVisitForm but a manager can pick any volunteer."""
    class Meta:
        model  = VolunteerVisit
        fields = ["volunteer", "visit_date", "hours", "activity_type", "notes"]
        widgets = {
            "visit_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class ManagerNotesForm(forms.ModelForm):
    class Meta:
        model  = Volunteer
        fields = ["notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}
