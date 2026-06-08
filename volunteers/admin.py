import json
from django.contrib import admin
from django.db import models as db_models
from django.utils.html import format_html
from .models import (
    SiteSettings, VolunteerApplication, AdminNotificationPreference,
    Volunteer, Shift, ShiftSignup, HourLog, GroupEmailRecord,
    AVAILABILITY_OPTIONS,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    pass


@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ["get_full_name", "email", "status", "submitted_at"]
    list_filter = ["status"]
    search_fields = ["first_name", "last_name", "email"]
    readonly_fields = [
        "submitted_at", "reviewed_at", "reviewed_by",
        "get_availability_display",
    ]
    # Exclude the raw JSONField from the form — display the readable version instead
    exclude = ["availability"]

    @admin.display(description="Name", ordering="last_name")
    def get_full_name(self, obj):
        return obj.full_name

    @admin.display(description="Availability")
    def get_availability_display(self, obj):
        labels = dict(AVAILABILITY_OPTIONS)
        items = [labels.get(k, k) for k in (obj.availability or [])]
        return ", ".join(items) if items else "—"


@admin.register(AdminNotificationPreference)
class AdminNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "notify_new_application"]


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ["get_full_name", "get_email", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["user__first_name", "user__last_name", "user__email"]

    @admin.display(description="Name", ordering="user__last_name")
    def get_full_name(self, obj):
        return obj.full_name

    @admin.display(description="Email", ordering="user__email")
    def get_email(self, obj):
        return obj.email


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ["title", "date", "start_time", "activity_type", "capacity", "get_signup_count", "is_cancelled"]
    list_filter = ["activity_type", "is_cancelled", "date"]
    search_fields = ["title"]

    @admin.display(description="Signups")
    def get_signup_count(self, obj):
        return obj.signup_count


@admin.register(ShiftSignup)
class ShiftSignupAdmin(admin.ModelAdmin):
    list_display = ["volunteer", "shift", "is_cancelled", "signed_up_at"]
    list_filter = ["is_cancelled"]


@admin.register(HourLog)
class HourLogAdmin(admin.ModelAdmin):
    list_display = ["volunteer_name", "date", "hours", "activity_type", "logged_at"]
    list_filter = ["activity_type", "date"]
    search_fields = ["volunteer_name"]


@admin.register(GroupEmailRecord)
class GroupEmailRecordAdmin(admin.ModelAdmin):
    list_display = ["subject", "sent_by", "sent_at", "recipient_count", "recipient_filter"]
    readonly_fields = ["sent_at"]
