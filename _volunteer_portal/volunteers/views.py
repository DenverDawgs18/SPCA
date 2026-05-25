from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count
from datetime import timedelta

from .models import Volunteer, VolunteerVisit, SiteSettings, ACTIVITY_CHOICES
from .forms import (
    RegistrationForm, ProfileForm, LogVisitForm,
    ManagerLogVisitForm, ManagerNotesForm,
)


# ─── Helpers ────────────────────────────────────────────────────────────────

def _require_manager(view_fn):
    """Decorator: user must be staff."""
    from functools import wraps
    @wraps(view_fn)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "You don't have permission to access the manager portal.")
            return redirect("vol_dashboard")
        return view_fn(request, *args, **kwargs)
    return wrapped


# ─── Auth ────────────────────────────────────────────────────────────────────

def vol_login(request):
    if request.user.is_authenticated:
        return redirect("vol_dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.POST.get("next") or "vol_dashboard")
        messages.error(request, "Invalid username or password.")
    return render(request, "volunteers/login.html", {"next": request.GET.get("next", "")})


def vol_logout(request):
    logout(request)
    return redirect("vol_login")


def vol_register(request):
    if request.user.is_authenticated:
        return redirect("vol_dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        user = User.objects.create_user(
            username=cd["username"],
            password=cd["password"],
            email=cd["email"],
            first_name=cd["first_name"],
            last_name=cd["last_name"],
        )
        Volunteer.objects.create(
            user=user,
            phone=cd["phone"],
            address=cd.get("address", ""),
            availability=cd.get("availability", []),
            skills=cd.get("skills", ""),
            emergency_contact_name=cd["emergency_contact_name"],
            emergency_contact_phone=cd["emergency_contact_phone"],
            emergency_contact_relationship=cd.get("emergency_contact_relationship", ""),
            t_shirt_size=cd.get("t_shirt_size", ""),
            is_approved=False,
        )
        messages.success(
            request,
            "Your application has been submitted! A volunteer manager will review it and be in touch soon."
        )
        return redirect("vol_login")
    return render(request, "volunteers/register.html", {"form": form})


# ─── Volunteer Portal ─────────────────────────────────────────────────────────

@login_required
def vol_dashboard(request):
    if request.user.is_staff:
        return redirect("mgr_dashboard")
    try:
        volunteer = request.user.volunteer_profile
    except Volunteer.DoesNotExist:
        messages.info(request, "Your volunteer profile isn't set up yet. Please contact a manager.")
        return render(request, "volunteers/dashboard.html", {"volunteer": None})

    if not volunteer.is_approved:
        return render(request, "volunteers/pending_approval.html", {"volunteer": volunteer})

    recent_visits = volunteer.visits.all()[:5]
    settings = SiteSettings.get()
    return render(request, "volunteers/dashboard.html", {
        "volunteer": volunteer,
        "recent_visits": recent_visits,
        "settings": settings,
        "is_active": volunteer.is_active(),
        "visit_window_count": volunteer.visit_count_in_window(),
        "total_hours": volunteer.total_hours(),
    })


@login_required
def vol_profile(request):
    try:
        volunteer = request.user.volunteer_profile
    except Volunteer.DoesNotExist:
        return redirect("vol_dashboard")

    form = ProfileForm(request.POST or None, instance=volunteer)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        request.user.first_name = cd["first_name"]
        request.user.last_name  = cd["last_name"]
        request.user.email      = cd["email"]
        request.user.save()
        v = form.save(commit=False)
        v.availability = cd.get("availability", [])
        v.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("vol_profile")

    return render(request, "volunteers/profile.html", {"form": form, "volunteer": volunteer})


@login_required
def vol_log_visit(request):
    try:
        volunteer = request.user.volunteer_profile
    except Volunteer.DoesNotExist:
        return redirect("vol_dashboard")
    if not volunteer.is_approved:
        return redirect("vol_dashboard")

    form = LogVisitForm(request.POST or None, initial={"visit_date": timezone.now().date()})
    if request.method == "POST" and form.is_valid():
        visit = form.save(commit=False)
        visit.volunteer  = volunteer
        visit.logged_by  = request.user
        visit.save()
        messages.success(request, f"Visit on {visit.visit_date} logged ({visit.hours}h — {visit.get_activity_type_display()}).")
        return redirect("vol_dashboard")

    return render(request, "volunteers/log_visit.html", {"form": form})


@login_required
def vol_visit_history(request):
    try:
        volunteer = request.user.volunteer_profile
    except Volunteer.DoesNotExist:
        return redirect("vol_dashboard")

    visits = volunteer.visits.all()
    total  = volunteer.total_hours()
    return render(request, "volunteers/visit_history.html", {
        "volunteer": volunteer,
        "visits": visits,
        "total_hours": total,
    })


# ─── Manager Portal ───────────────────────────────────────────────────────────

@_require_manager
def mgr_dashboard(request):
    settings = SiteSettings.get()
    cutoff = timezone.now().date() - timedelta(days=settings.inactivity_days)

    all_volunteers = Volunteer.objects.filter(is_approved=True).select_related("user")
    pending_count  = Volunteer.objects.filter(is_approved=False).count()

    active_ids   = []
    inactive_ids = []
    for v in all_volunteers:
        if v.is_active():
            active_ids.append(v.pk)
        else:
            inactive_ids.append(v.pk)

    recent_visits = VolunteerVisit.objects.select_related("volunteer__user").all()[:10]

    return render(request, "volunteers/manager/dashboard.html", {
        "total_volunteers": all_volunteers.count(),
        "active_count": len(active_ids),
        "inactive_count": len(inactive_ids),
        "pending_count": pending_count,
        "recent_visits": recent_visits,
        "settings": settings,
    })


@_require_manager
def mgr_volunteer_list(request):
    settings = SiteSettings.get()
    qs = Volunteer.objects.filter(is_approved=True).select_related("user")

    # Filter: active / inactive
    status_filter = request.GET.get("status", "")
    search = request.GET.get("q", "").strip()

    if search:
        qs = qs.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)  |
            Q(user__email__icontains=search)       |
            Q(phone__icontains=search)
        )

    volunteers = list(qs)

    # Tag active/inactive then optionally filter
    for v in volunteers:
        v._is_active = v.is_active()
        v._last_visit = v.last_visit()
        v._window_visits = v.visit_count_in_window()

    if status_filter == "active":
        volunteers = [v for v in volunteers if v._is_active]
    elif status_filter == "inactive":
        volunteers = [v for v in volunteers if not v._is_active]

    # Sort: inactive first by default so managers can act quickly
    volunteers.sort(key=lambda v: (v._is_active, v._last_visit.visit_date if v._last_visit else ""))

    return render(request, "volunteers/manager/volunteer_list.html", {
        "volunteers": volunteers,
        "status_filter": status_filter,
        "search": search,
        "settings": settings,
        "inactive_count": sum(1 for v in volunteers if not v._is_active),
    })


@_require_manager
def mgr_volunteer_detail(request, pk):
    volunteer = get_object_or_404(Volunteer, pk=pk)
    settings  = SiteSettings.get()
    notes_form = ManagerNotesForm(request.POST or None, instance=volunteer)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_notes" and notes_form.is_valid():
            notes_form.save()
            messages.success(request, "Notes saved.")
            return redirect("mgr_volunteer_detail", pk=pk)
        elif action == "log_visit":
            log_form = ManagerLogVisitForm(request.POST)
            if log_form.is_valid():
                visit = log_form.save(commit=False)
                visit.volunteer = volunteer
                visit.logged_by = request.user
                visit.save()
                messages.success(request, f"Visit logged for {volunteer}.")
                return redirect("mgr_volunteer_detail", pk=pk)
        elif action == "delete_visit":
            visit_id = request.POST.get("visit_id")
            VolunteerVisit.objects.filter(pk=visit_id, volunteer=volunteer).delete()
            messages.success(request, "Visit deleted.")
            return redirect("mgr_volunteer_detail", pk=pk)

    log_form = ManagerLogVisitForm(initial={
        "volunteer": volunteer,
        "visit_date": timezone.now().date(),
    })
    log_form.fields["volunteer"].widget = log_form.fields["volunteer"].hidden_widget()

    visits = volunteer.visits.all()
    return render(request, "volunteers/manager/volunteer_detail.html", {
        "volunteer": volunteer,
        "visits": visits,
        "notes_form": notes_form,
        "log_form": log_form,
        "settings": settings,
        "is_active": volunteer.is_active(),
        "window_visits": volunteer.visit_count_in_window(),
        "total_hours": volunteer.total_hours(),
        "last_visit": volunteer.last_visit(),
    })


@_require_manager
def mgr_pending(request):
    pending = Volunteer.objects.filter(is_approved=False).select_related("user").order_by("created_at")
    if request.method == "POST":
        action = request.POST.get("action")
        vol_id = request.POST.get("volunteer_id")
        v = get_object_or_404(Volunteer, pk=vol_id)
        if action == "approve":
            v.is_approved = True
            v.approved_by = request.user
            v.approved_at = timezone.now()
            v.save()
            messages.success(request, f"{v} has been approved.")
        elif action == "deny":
            v.user.delete()  # also deletes volunteer via cascade
            messages.warning(request, "Application denied and account removed.")
        return redirect("mgr_pending")

    return render(request, "volunteers/manager/pending_approvals.html", {"pending": pending})


@_require_manager
def mgr_settings(request):
    settings_obj = SiteSettings.get()
    if request.method == "POST":
        try:
            days = int(request.POST.get("inactivity_days", 90))
            min_visits = int(request.POST.get("inactivity_min_visits", 2))
            if days < 1 or min_visits < 1:
                raise ValueError
            settings_obj.inactivity_days = days
            settings_obj.inactivity_min_visits = min_visits
            settings_obj.save()
            messages.success(request, "Settings updated.")
        except (ValueError, TypeError):
            messages.error(request, "Please enter valid positive integers.")
        return redirect("mgr_settings")

    return render(request, "volunteers/manager/settings.html", {"settings": settings_obj})
