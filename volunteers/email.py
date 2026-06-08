"""
Email helpers for the volunteer portal.

All notification emails use fail_silently=True so they never crash a request.
"""

from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.conf import settings as django_settings


def _from_email():
    from .models import SiteSettings
    site = SiteSettings.get()
    return site.notification_from_email or django_settings.DEFAULT_FROM_EMAIL


# ---------------------------------------------------------------------------
# Applicant-facing emails
# ---------------------------------------------------------------------------

def send_application_received(application):
    """Confirm receipt of a new application to the applicant."""
    subject = "We received your volunteer application — Medina County SPCA"
    body = (
        f"Hi {application.first_name},\n\n"
        "Thank you for applying to volunteer with the Medina County SPCA! "
        "We have received your application and will review it shortly.\n\n"
        "If your application is approved, you will receive a separate email "
        "with instructions to set your password and access the volunteer portal.\n\n"
        "Questions? Reply to this email or call us at (330) 723-7722.\n\n"
        "— Medina County SPCA Volunteer Team"
    )
    try:
        send_mail(
            subject,
            body,
            _from_email(),
            [application.email],
            fail_silently=True,
        )
    except Exception:
        pass


def send_application_approved(application, set_password_url):
    """Tell an approved applicant how to set their password."""
    subject = "Your volunteer application was approved! — Medina County SPCA"
    body = (
        f"Hi {application.first_name},\n\n"
        "Great news — your volunteer application has been approved! "
        "We're thrilled to have you join our team.\n\n"
        "To get started, please set your password by clicking the link below "
        "(valid for 72 hours):\n\n"
        f"  {set_password_url}\n\n"
        "Once you've set your password, you can log in at:\n"
        "  https://medinacountyspca.com/portal/login/\n\n"
        "From there you'll be able to browse upcoming shifts, log your hours, "
        "and manage your profile.\n\n"
        "See you at the shelter!\n\n"
        "— Medina County SPCA Volunteer Team"
    )
    try:
        send_mail(
            subject,
            body,
            _from_email(),
            [application.email],
            fail_silently=True,
        )
    except Exception:
        pass


def send_application_denied(application):
    """Notify an applicant that their application was denied."""
    subject = "Update on your volunteer application — Medina County SPCA"
    reason_section = ""
    if application.denial_reason:
        reason_section = f"\nReason provided:\n{application.denial_reason}\n"
    body = (
        f"Hi {application.first_name},\n\n"
        "Thank you for your interest in volunteering with the Medina County SPCA. "
        "After reviewing your application, we are unable to move forward at this time.\n"
        f"{reason_section}\n"
        "We appreciate your support for the animals in our care. "
        "You are welcome to reapply in the future.\n\n"
        "Questions? Contact us at info@medinacountyspca.com or (330) 723-7722.\n\n"
        "— Medina County SPCA Volunteer Team"
    )
    try:
        send_mail(
            subject,
            body,
            _from_email(),
            [application.email],
            fail_silently=True,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Admin notification email
# ---------------------------------------------------------------------------

def notify_admins_new_application(application, request):
    """Send a notification to all opted-in staff about a new application."""
    from .models import AdminNotificationPreference

    # Build the absolute URL to the application detail page
    detail_path = f"/portal/manager/applications/{application.pk}/"
    try:
        detail_url = request.build_absolute_uri(detail_path)
    except Exception:
        detail_url = f"https://medinacountyspca.com{detail_path}"

    subject = f"New volunteer application from {application.full_name}"
    body = (
        f"A new volunteer application has been submitted.\n\n"
        f"Name:  {application.full_name}\n"
        f"Email: {application.email}\n"
        f"Phone: {application.phone}\n"
        f"Submitted: {application.submitted_at:%Y-%m-%d %H:%M}\n\n"
        f"Review the application here:\n{detail_url}\n\n"
        "— Medina County SPCA Volunteer Portal"
    )

    # Find staff users who have opted in (create preference row if missing)
    staff_users = User.objects.filter(is_staff=True, is_active=True)
    recipients = []
    for user in staff_users:
        pref, _ = AdminNotificationPreference.objects.get_or_create(user=user)
        if pref.notify_new_application and user.email:
            recipients.append(user.email)

    if recipients:
        try:
            send_mail(
                subject,
                body,
                _from_email(),
                recipients,
                fail_silently=True,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Group email
# ---------------------------------------------------------------------------

def send_group_email(subject, body, recipient_emails, from_email=None):
    """Send a message to a list of volunteer email addresses."""
    if not recipient_emails:
        return 0

    sender = from_email or _from_email()
    sent = 0
    for email in recipient_emails:
        try:
            send_mail(subject, body, sender, [email], fail_silently=True)
            sent += 1
        except Exception:
            pass
    return sent
