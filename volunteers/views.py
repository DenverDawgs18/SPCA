"""
Volunteer portal views.

URL namespace: 'volunteers'
All manager views require is_staff.
"""

import csv
import io
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .email import (
    notify_admins_new_application,
    send_application_approved,
    send_application_denied,
    send_application_received,
)
from .forms import (
    ApplicationForm,
    DenyForm,
    GroupEmailForm,
    HourLogKioskForm,
    ManagerNotesForm,
    ShiftForm,
    SiteSettingsForm,
    VolunteerImportForm,
    VolunteerScheduleForm,
)
from .models import ACTIVITY_CHOICES
from .models import (
    AdminNotificationPreference,
    GroupEmailRecord,
    HourLog,
    Shift,
    ShiftSignup,
    SiteSettings,
    Volunteer,
    VolunteerApplication,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_manager(view_func):
    """Decorator: user must be is_staff, else redirect to dashboard with error."""
    @wraps(view_func)
    @login_required(login_url="/portal/login/")
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "You don't have permission to access the manager portal.")
            return redirect("volunteers:dashboard")
        return view_func(request, *args, **kwargs)
    return wrapped


def _get_volunteer_or_redirect(request):
    """Return the Volunteer profile or None (caller should handle)."""
    try:
        return request.user.volunteer_profile
    except Volunteer.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

def portal_home(request):
    """Redirect to dashboard if logged in, else login."""
    if request.user.is_authenticated:
        return redirect("volunteers:dashboard")
    return redirect("volunteers:login")


def vol_login(request):
    if request.user.is_authenticated:
        return redirect("volunteers:dashboard")

    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Allow login with email address — look up the username first
        if "@" in username:
            try:
                matched = User.objects.get(email__iexact=username)
                username = matched.username
            except User.DoesNotExist:
                pass

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url or "volunteers:dashboard")
        messages.error(request, "Invalid username/email or password. Please try again.")

    return render(request, "volunteers/login.html", {"next": next_url})


def vol_logout(request):
    if request.method == "POST":
        logout(request)
    return redirect("/")


def apply(request):
    form = ApplicationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        application = form.save(commit=False)
        application.status = "pending"
        # JSONField — save list from MultipleChoiceField
        application.availability = form.cleaned_data.get("availability", [])
        application.save()
        send_application_received(application)
        notify_admins_new_application(application, request)
        return redirect("volunteers:apply_success")

    return render(request, "volunteers/apply.html", {"form": form})


def apply_success(request):
    return render(request, "volunteers/apply_success.html")


def kiosk_log_hours(request):
    success_name = None
    form = HourLogKioskForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        volunteer = form.cleaned_data["volunteer"]
        log = HourLog(
            volunteer=volunteer,
            volunteer_name=volunteer.full_name,
            date=form.cleaned_data["date"],
            hours=form.cleaned_data["hours"],
            activity_type=form.cleaned_data["activity_type"],
            notes=form.cleaned_data.get("notes", ""),
        )
        log.save()
        success_name = volunteer.full_name
        form = HourLogKioskForm()  # clear form for next person

    return render(request, "volunteers/log_hours.html", {
        "form": form,
        "success_name": success_name,
    })


# ---------------------------------------------------------------------------
# Volunteer-facing views (login required)
# ---------------------------------------------------------------------------

@login_required(login_url="/portal/login/")
def vol_dashboard(request):
    if request.user.is_staff:
        return redirect("volunteers:mgr_dashboard")

    volunteer = _get_volunteer_or_redirect(request)
    if volunteer is None:
        messages.info(request, "Your volunteer profile isn't set up yet. Please contact a manager.")
        return render(request, "volunteers/dashboard.html", {"volunteer": None})

    today = timezone.now().date()
    upcoming_signups = (
        ShiftSignup.objects
        .filter(volunteer=volunteer, is_cancelled=False, shift__date__gte=today)
        .select_related("shift")
        .order_by("shift__date", "shift__start_time")[:5]
    )
    recent_logs = volunteer.hour_logs.all()[:5]

    return render(request, "volunteers/dashboard.html", {
        "volunteer": volunteer,
        "upcoming_signups": upcoming_signups,
        "recent_logs": recent_logs,
        "total_hours": volunteer.total_hours,
        "is_inactive": volunteer.is_inactive(),
    })


@login_required(login_url="/portal/login/")
def vol_schedule(request):
    volunteer = _get_volunteer_or_redirect(request)
    if volunteer is None:
        messages.error(request, "Volunteer profile not found.")
        return redirect("volunteers:dashboard")

    form = VolunteerScheduleForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        activity = form.cleaned_data["activity_type"]
        activity_label = dict(ACTIVITY_CHOICES).get(activity, activity)
        shift = Shift.objects.create(
            title=activity_label,
            description=form.cleaned_data.get("notes", ""),
            date=form.cleaned_data["date"],
            start_time=form.cleaned_data["start_time"],
            end_time=form.cleaned_data["end_time"],
            activity_type=activity,
            capacity=1,
            created_by=request.user,
        )
        ShiftSignup.objects.create(volunteer=volunteer, shift=shift)
        messages.success(request, f"Shift scheduled for {shift.date}!")
        return redirect("volunteers:my_shifts")

    today = timezone.now().date()
    upcoming = (
        ShiftSignup.objects
        .filter(volunteer=volunteer, is_cancelled=False, shift__date__gte=today)
        .select_related("shift")
        .order_by("shift__date", "shift__start_time")
    )

    return render(request, "volunteers/schedule.html", {
        "volunteer": volunteer,
        "form": form,
        "upcoming": upcoming,
    })


@login_required(login_url="/portal/login/")
def vol_shift_cancel(request, shift_id):
    if request.method != "POST":
        return redirect("volunteers:my_shifts")

    volunteer = _get_volunteer_or_redirect(request)
    if volunteer is None:
        return redirect("volunteers:dashboard")

    signup = get_object_or_404(ShiftSignup, shift_id=shift_id, volunteer=volunteer, is_cancelled=False)
    signup.is_cancelled = True
    signup.cancelled_at = timezone.now()
    signup.save()
    messages.success(request, "Your shift signup has been cancelled.")
    return redirect("volunteers:my_shifts")


@login_required(login_url="/portal/login/")
def vol_my_shifts(request):
    volunteer = _get_volunteer_or_redirect(request)
    if volunteer is None:
        return redirect("volunteers:dashboard")

    today = timezone.now().date()
    upcoming = (
        ShiftSignup.objects
        .filter(volunteer=volunteer, is_cancelled=False, shift__date__gte=today)
        .select_related("shift")
        .order_by("shift__date", "shift__start_time")
    )
    past = (
        ShiftSignup.objects
        .filter(volunteer=volunteer, is_cancelled=False, shift__date__lt=today)
        .select_related("shift")
        .order_by("-shift__date")[:20]
    )

    return render(request, "volunteers/my_shifts.html", {
        "volunteer": volunteer,
        "upcoming": upcoming,
        "past": past,
    })


@login_required(login_url="/portal/login/")
def vol_profile(request):
    volunteer = _get_volunteer_or_redirect(request)
    if volunteer is None:
        return redirect("volunteers:dashboard")

    if request.method == "POST":
        # Allow editing emergency contact and phone via simple POST
        application = volunteer.application
        if application:
            application.emergency_contact_name = request.POST.get("emergency_contact_name", application.emergency_contact_name)
            application.emergency_contact_phone = request.POST.get("emergency_contact_phone", application.emergency_contact_phone)
            application.emergency_contact_relationship = request.POST.get("emergency_contact_relationship", application.emergency_contact_relationship)
            application.phone = request.POST.get("phone", application.phone)
            application.save()
        messages.success(request, "Profile updated.")
        return redirect("volunteers:profile")

    return render(request, "volunteers/profile.html", {"volunteer": volunteer})


# ---------------------------------------------------------------------------
# Manager views
# ---------------------------------------------------------------------------

@_require_manager
def mgr_dashboard(request):
    today = timezone.now().date()
    pending_count = VolunteerApplication.objects.filter(status="pending").count()
    total_volunteers = Volunteer.objects.count()
    active_volunteers = Volunteer.objects.filter(is_active=True).count()
    todays_shifts = Shift.objects.filter(date=today, is_cancelled=False).count()

    recent_logs = HourLog.objects.select_related("volunteer__user").all()[:10]

    return render(request, "volunteers/manager/dashboard.html", {
        "pending_count": pending_count,
        "total_volunteers": total_volunteers,
        "active_volunteers": active_volunteers,
        "todays_shifts": todays_shifts,
        "recent_logs": recent_logs,
    })


@_require_manager
def mgr_applications(request):
    pending = VolunteerApplication.objects.filter(status="pending").order_by("submitted_at")
    reviewed = VolunteerApplication.objects.exclude(status="pending").order_by("-reviewed_at")[:20]

    return render(request, "volunteers/manager/applications.html", {
        "pending": pending,
        "reviewed": reviewed,
        "pending_count": pending.count(),
    })


@_require_manager
def mgr_application_detail(request, app_id):
    application = get_object_or_404(VolunteerApplication, pk=app_id)
    deny_form = DenyForm()

    return render(request, "volunteers/manager/application_detail.html", {
        "application": application,
        "deny_form": deny_form,
        "pending_count": VolunteerApplication.objects.filter(status="pending").count(),
    })


@_require_manager
def mgr_approve(request, app_id):
    if request.method != "POST":
        return redirect("volunteers:mgr_application_detail", app_id=app_id)

    application = get_object_or_404(VolunteerApplication, pk=app_id)

    if application.status != "pending":
        messages.error(request, "This application has already been reviewed.")
        return redirect("volunteers:mgr_application_detail", app_id=app_id)

    # Create or reuse user
    email_lower = application.email.lower()
    existing_user = User.objects.filter(email__iexact=application.email).first()
    if existing_user:
        user = existing_user
        user.first_name = application.first_name
        user.last_name = application.last_name
        user.save()
    else:
        # Ensure unique username
        base_username = email_lower
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        user = User.objects.create_user(
            username=username,
            email=application.email,
            first_name=application.first_name,
            last_name=application.last_name,
        )
        user.set_unusable_password()
        user.save()

    # Link application to user
    application.user = user
    application.status = "approved"
    application.reviewed_at = timezone.now()
    application.reviewed_by = request.user
    application.save()

    # Create volunteer record
    volunteer, _ = Volunteer.objects.get_or_create(user=user)
    if not volunteer.application:
        volunteer.application = application
        volunteer.save()

    # Build set-password URL
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    set_password_url = request.build_absolute_uri(
        f"/portal/set-password/{uid}/{token}/"
    )

    send_application_approved(application, set_password_url)
    messages.success(request, f"Application approved. Welcome email sent to {application.email}.")
    return redirect("volunteers:mgr_applications")


@_require_manager
def mgr_deny(request, app_id):
    if request.method != "POST":
        return redirect("volunteers:mgr_application_detail", app_id=app_id)

    application = get_object_or_404(VolunteerApplication, pk=app_id)
    form = DenyForm(request.POST)
    if form.is_valid():
        application.denial_reason = form.cleaned_data["denial_reason"]
        application.status = "denied"
        application.reviewed_at = timezone.now()
        application.reviewed_by = request.user
        application.save()
        send_application_denied(application)
        messages.success(request, f"Application denied. Notification sent to {application.email}.")
    else:
        messages.error(request, "Please provide a reason for denial.")

    return redirect("volunteers:mgr_applications")


@_require_manager
def mgr_volunteers(request):
    qs = Volunteer.objects.select_related("user", "application")
    status_filter = request.GET.get("status", "active")
    search = request.GET.get("q", "").strip()

    if search:
        qs = qs.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search)
        )

    if status_filter == "active":
        qs = qs.filter(is_active=True)
    elif status_filter == "inactive":
        qs = qs.filter(is_active=False)

    volunteers = list(qs)
    for v in volunteers:
        v.inactivity_flag = v.is_inactive()

    return render(request, "volunteers/manager/volunteers.html", {
        "volunteers": volunteers,
        "status_filter": status_filter,
        "search": search,
        "pending_count": VolunteerApplication.objects.filter(status="pending").count(),
    })


@_require_manager
def mgr_volunteer_detail(request, vol_id):
    volunteer = get_object_or_404(Volunteer, pk=vol_id)
    notes_form = ManagerNotesForm(instance=volunteer)

    if request.method == "POST":
        notes_form = ManagerNotesForm(request.POST, instance=volunteer)
        if notes_form.is_valid():
            notes_form.save()
            messages.success(request, "Notes saved.")
        return redirect("volunteers:mgr_volunteer_detail", vol_id=vol_id)

    recent_logs = volunteer.hour_logs.all()[:10]
    upcoming_signups = (
        ShiftSignup.objects
        .filter(volunteer=volunteer, is_cancelled=False, shift__date__gte=timezone.now().date())
        .select_related("shift")
        .order_by("shift__date")[:10]
    )

    return render(request, "volunteers/manager/volunteer_detail.html", {
        "volunteer": volunteer,
        "notes_form": notes_form,
        "recent_logs": recent_logs,
        "upcoming_signups": upcoming_signups,
        "is_inactive": volunteer.is_inactive(),
        "total_hours": volunteer.total_hours,
        "pending_count": VolunteerApplication.objects.filter(status="pending").count(),
    })


@_require_manager
def mgr_toggle_active(request, vol_id):
    if request.method != "POST":
        return redirect("volunteers:mgr_volunteers")
    volunteer = get_object_or_404(Volunteer, pk=vol_id)
    volunteer.is_active = not volunteer.is_active
    volunteer.save()
    state = "activated" if volunteer.is_active else "deactivated"
    messages.success(request, f"{volunteer.full_name} has been {state}.")
    return redirect("volunteers:mgr_volunteer_detail", vol_id=vol_id)


@_require_manager
def mgr_shifts(request):
    today = timezone.now().date()
    upcoming = (
        Shift.objects
        .filter(date__gte=today)
        .prefetch_related("shiftsignup_set__volunteer__user")
        .order_by("date", "start_time")
    )
    past = (
        Shift.objects
        .filter(date__lt=today)
        .prefetch_related("shiftsignup_set__volunteer__user")
        .order_by("-date")[:30]
    )

    return render(request, "volunteers/manager/shifts.html", {
        "upcoming": upcoming,
        "past": past,
        "pending_count": VolunteerApplication.objects.filter(status="pending").count(),
    })


@_require_manager
def mgr_shift_create(request):
    form = ShiftForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        shift = form.save(commit=False)
        shift.created_by = request.user
        shift.save()
        messages.success(request, f"Shift '{shift.title}' created.")
        return redirect("volunteers:mgr_shifts")

    return render(request, "volunteers/manager/shift_form.html", {
        "form": form,
        "action": "Create",
        "pending_count": VolunteerApplication.objects.filter(status="pending").count(),
    })


@_require_manager
def mgr_shift_detail(request, shift_id):
    shift = get_object_or_404(Shift, pk=shift_id)
    signups = ShiftSignup.objects.filter(shift=shift, is_cancelled=False).select_related("volunteer__user")
    hour_logs = HourLog.objects.filter(shift=shift).select_related("volunteer__user")

    return render(request, "volunteers/manager/shift_detail.html", {
        "shift": shift,
        "signups": signups,
        "hour_logs": hour_logs,
        "pending_count": VolunteerApplication.objects.filter(status="pending").count(),
    })


@_require_manager
def mgr_shift_edit(request, shift_id):
    shift = get_object_or_404(Shift, pk=shift_id)
    form = ShiftForm(request.POST or None, instance=shift)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Shift updated.")
        return redirect("volunteers:mgr_shift_detail", shift_id=shift_id)

    return render(request, "volunteers/manager/shift_form.html", {
        "form": form,
        "action": "Edit",
        "shift": shift,
        "pending_count": VolunteerApplication.objects.filter(status="pending").count(),
    })


@_require_manager
def mgr_shift_delete(request, shift_id):
    if request.method != "POST":
        return redirect("volunteers:mgr_shifts")
    shift = get_object_or_404(Shift, pk=shift_id)
    shift.is_cancelled = True
    shift.save()
    messages.success(request, f"Shift '{shift.title}' has been cancelled.")
    return redirect("volunteers:mgr_shifts")


@_require_manager
def mgr_hour_logs(request):
    qs = HourLog.objects.select_related("volunteer__user", "shift").all()

    search = request.GET.get("q", "").strip()
    date_filter = request.GET.get("date", "").strip()

    if search:
        qs = qs.filter(volunteer_name__icontains=search)

    if date_filter:
        try:
            from datetime import datetime
            d = datetime.strptime(date_filter, "%Y-%m-%d").date()
            qs = qs.filter(date=d)
        except ValueError:
            pass

    paginator = Paginator(qs, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "volunteers/manager/hour_logs.html", {
        "page_obj": page_obj,
        "search": search,
        "date_filter": date_filter,
        "pending_count": VolunteerApplication.objects.filter(status="pending").count(),
    })


@_require_manager
def mgr_hour_log_delete(request, log_id):
    if request.method != "POST":
        return redirect("volunteers:mgr_hour_logs")
    log = get_object_or_404(HourLog, pk=log_id)
    log.delete()
    messages.success(request, "Hour log deleted.")
    return redirect("volunteers:mgr_hour_logs")


@_require_manager
def mgr_group_email(request):
    all_vols = Volunteer.objects.filter(is_active=True)
    inactive_vols = Volunteer.objects.filter(is_active=False)
    all_count = Volunteer.objects.count()
    active_count = all_vols.count()
    inactive_count = inactive_vols.count()

    form = GroupEmailForm(request.POST or None)
    prepared = None

    if request.method == "POST" and form.is_valid():
        subject = form.cleaned_data["subject"]
        body = form.cleaned_data["body"]
        recipient_filter = form.cleaned_data["recipient_filter"]

        if recipient_filter == "active":
            recipients_qs = Volunteer.objects.filter(is_active=True)
        elif recipient_filter == "inactive":
            recipients_qs = Volunteer.objects.filter(is_active=False)
        else:
            recipients_qs = Volunteer.objects.all()

        recipient_emails = list(
            recipients_qs.exclude(user__email="").values_list("user__email", flat=True)
        )

        GroupEmailRecord.objects.create(
            subject=subject,
            body=body,
            sent_by=request.user,
            recipient_count=len(recipient_emails),
            recipient_filter=recipient_filter,
        )

        filter_labels = {"all": "All volunteers", "active": "Active volunteers", "inactive": "Inactive volunteers"}
        prepared = {
            "subject": subject,
            "body": body,
            "emails": recipient_emails,
            "emails_csv": ", ".join(recipient_emails),
            "count": len(recipient_emails),
            "filter_label": filter_labels.get(recipient_filter, recipient_filter),
        }
        form = GroupEmailForm()  # reset form for a fresh compose after

    recent_emails = GroupEmailRecord.objects.all()[:10]

    return render(request, "volunteers/manager/group_email.html", {
        "form": form,
        "prepared": prepared,
        "all_count": all_count,
        "active_count": active_count,
        "inactive_count": inactive_count,
        "recent_emails": recent_emails,
        "pending_count": VolunteerApplication.objects.filter(status="pending").count(),
    })


@_require_manager
def mgr_settings(request):
    settings_obj = SiteSettings.get()
    pref, _ = AdminNotificationPreference.objects.get_or_create(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save_settings":
            form = SiteSettingsForm(request.POST)
            if form.is_valid():
                settings_obj.inactivity_days = form.cleaned_data["inactivity_days"]
                settings_obj.inactivity_min_visits = form.cleaned_data["inactivity_min_visits"]
                settings_obj.save()
                messages.success(request, "Settings updated.")
            else:
                messages.error(request, "Please correct the errors below.")
        elif action == "toggle_notification":
            pref.notify_new_application = not pref.notify_new_application
            pref.save()
            state = "enabled" if pref.notify_new_application else "disabled"
            messages.success(request, f"New application notifications {state}.")

        return redirect("volunteers:mgr_settings")

    form = SiteSettingsForm(initial={
        "inactivity_days": settings_obj.inactivity_days,
        "inactivity_min_visits": settings_obj.inactivity_min_visits,
    })

    return render(request, "volunteers/manager/settings.html", {
        "form": form,
        "settings": settings_obj,
        "pref": pref,
        "pending_count": VolunteerApplication.objects.filter(status="pending").count(),
    })


# ---------------------------------------------------------------------------
# CSV volunteer import
# ---------------------------------------------------------------------------

# Columns we recognise (normalised: lowercase, underscores)
_REQUIRED_COLS = {"first_name", "last_name", "email"}
_OPTIONAL_COLS = {"phone", "notes"}


def _normalise_header(h):
    return h.strip().lower().replace(" ", "_").replace("-", "_")


@_require_manager
def mgr_import_volunteers(request):
    pending_count = VolunteerApplication.objects.filter(status="pending").count()

    if request.method != "POST":
        return render(request, "volunteers/manager/import_volunteers.html", {
            "form": VolunteerImportForm(),
            "pending_count": pending_count,
        })

    form = VolunteerImportForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "volunteers/manager/import_volunteers.html", {
            "form": form,
            "pending_count": pending_count,
        })

    raw = request.FILES["csv_file"].read()
    try:
        text = raw.decode("utf-8-sig")  # handle Excel BOM
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    headers = {_normalise_header(h) for h in (reader.fieldnames or [])}
    missing = _REQUIRED_COLS - headers
    if missing:
        form.add_error(
            "csv_file",
            f"Missing required column(s): {', '.join(sorted(missing))}. "
            "Found: " + ", ".join(sorted(headers)) + "."
        )
        return render(request, "volunteers/manager/import_volunteers.html", {
            "form": form,
            "pending_count": pending_count,
        })

    created, skipped, errors = [], [], []

    for row_num, raw_row in enumerate(reader, start=2):
        row = {_normalise_header(k): (v or "").strip() for k, v in raw_row.items()}

        first = row.get("first_name", "")
        last  = row.get("last_name", "")
        email = row.get("email", "").lower()
        phone = row.get("phone", "")
        notes = row.get("notes", "")

        if not email:
            errors.append({"row": row_num, "name": f"{first} {last}".strip() or "(blank)", "reason": "Email is blank."})
            continue

        if not first or not last:
            errors.append({"row": row_num, "name": email, "reason": "first_name or last_name is blank."})
            continue

        if User.objects.filter(email__iexact=email).exists():
            skipped.append({"row": row_num, "name": f"{first} {last}", "email": email,
                            "reason": "A user with this email already exists."})
            continue

        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first,
                last_name=last,
                password=None,
            )
            user.set_unusable_password()
            user.save()
            Volunteer.objects.create(user=user, is_active=True, notes=notes)
            created.append({"name": f"{first} {last}", "email": email})
        except Exception as exc:
            errors.append({"row": row_num, "name": f"{first} {last}", "reason": str(exc)})

    return render(request, "volunteers/manager/import_volunteers.html", {
        "form": VolunteerImportForm(),
        "results": {"created": created, "skipped": skipped, "errors": errors},
        "pending_count": pending_count,
    })
