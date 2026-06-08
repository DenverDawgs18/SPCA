"""
Email helpers for the volunteer portal.

Uses Django's send_mail backed by whatever EMAIL_* settings are configured.
Failures are logged rather than silently swallowed so they appear in Fly logs.
"""

import logging

from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)


def _from_email():
    from .models import SiteSettings
    site = SiteSettings.get()
    return site.notification_from_email or django_settings.DEFAULT_FROM_EMAIL


def _send(subject, body, recipients):
    """Send one email and log any failure. Returns True on success."""
    try:
        send_mail(subject, body, _from_email(), recipients, fail_silently=False)
        return True
    except Exception as exc:
        logger.error("Email send failed — subject: %r, to: %r — %s", subject, recipients, exc)
        return False


# ---------------------------------------------------------------------------
# Applicant-facing emails
# ---------------------------------------------------------------------------

def send_application_received(application):
    body = (
        f"Hi {application.first_name},\n\n"
        "Thank you for applying to volunteer with the Medina County SPCA! "
        "We have received your application and will review it shortly.\n\n"
        "If your application is approved you will receive a separate email "
        "with instructions to set your password and access the volunteer portal.\n\n"
        "Questions? Reply to this email or call us at (330) 723-7722.\n\n"
        "The Medina County SPCA Volunteer Team"
    )
    _send(
        "We received your volunteer application — Medina County SPCA",
        body,
        [application.email],
    )


def send_application_approved(application, set_password_url):
    body = (
        f"Hi {application.first_name},\n\n"
        "Great news — your volunteer application has been approved! "
        "We are thrilled to have you join our team.\n\n"
        "To get started, please set your password by clicking the link below "
        "(valid for 72 hours):\n\n"
        f"  {set_password_url}\n\n"
        "Once you have set your password you can log in at:\n"
        "  https://medinacountyspca.com/portal/login/\n\n"
        "From there you will be able to browse upcoming shifts, log your hours, "
        "and manage your profile.\n\n"
        "See you at the shelter!\n\n"
        "The Medina County SPCA Volunteer Team"
    )
    _send(
        "Your volunteer application was approved! — Medina County SPCA",
        body,
        [application.email],
    )


def send_application_denied(application):
    reason_section = ""
    if application.denial_reason:
        reason_section = f"\nReason:\n{application.denial_reason}\n"
    body = (
        f"Hi {application.first_name},\n\n"
        "Thank you for your interest in volunteering with the Medina County SPCA. "
        "After reviewing your application, we are unable to move forward at this time.\n"
        f"{reason_section}\n"
        "We appreciate your support for the animals in our care. "
        "You are welcome to reapply in the future.\n\n"
        "Questions? Contact us at info@medinacountyspca.com or (330) 723-7722.\n\n"
        "The Medina County SPCA Volunteer Team"
    )
    _send(
        "Update on your volunteer application — Medina County SPCA",
        body,
        [application.email],
    )


# ---------------------------------------------------------------------------
# Admin notification
# ---------------------------------------------------------------------------

def notify_admins_new_application(application, request):
    from .models import AdminNotificationPreference

    detail_path = f"/portal/manager/applications/{application.pk}/"
    try:
        detail_url = request.build_absolute_uri(detail_path)
    except Exception:
        detail_url = f"https://medinacountyspca.com{detail_path}"

    body = (
        f"A new volunteer application has been submitted.\n\n"
        f"Name:      {application.full_name}\n"
        f"Email:     {application.email}\n"
        f"Phone:     {application.phone}\n"
        f"Submitted: {application.submitted_at:%Y-%m-%d %H:%M}\n\n"
        f"Review it here:\n{detail_url}\n\n"
        "Medina County SPCA Volunteer Portal"
    )

    staff_users = User.objects.filter(is_staff=True, is_active=True)
    recipients = []
    for user in staff_users:
        pref, _ = AdminNotificationPreference.objects.get_or_create(user=user)
        if pref.notify_new_application and user.email:
            recipients.append(user.email)

    if recipients:
        _send(f"New volunteer application from {application.full_name}", body, recipients)
