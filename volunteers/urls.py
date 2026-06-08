from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = "volunteers"

urlpatterns = [
    path("", views.portal_home, name="home"),
    path("login/", views.vol_login, name="login"),
    path("logout/", views.vol_logout, name="logout"),
    path("apply/", views.apply, name="apply"),
    path("apply/success/", views.apply_success, name="apply_success"),
    path("log-hours/", views.kiosk_log_hours, name="log_hours"),
    path(
        "set-password/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="volunteers/set_password.html",
            success_url="/portal/login/",
        ),
        name="password_reset_confirm",
    ),
    # Volunteer pages
    path("dashboard/", views.vol_dashboard, name="dashboard"),
    path("schedule/", views.vol_schedule, name="schedule"),
    path("schedule/<int:shift_id>/signup/", views.vol_shift_signup, name="shift_signup"),
    path("schedule/<int:shift_id>/cancel/", views.vol_shift_cancel, name="shift_cancel"),
    path("my-shifts/", views.vol_my_shifts, name="my_shifts"),
    path("profile/", views.vol_profile, name="profile"),
    # Manager pages
    path("manager/", views.mgr_dashboard, name="mgr_dashboard"),
    path("manager/applications/", views.mgr_applications, name="mgr_applications"),
    path("manager/applications/<int:app_id>/", views.mgr_application_detail, name="mgr_application_detail"),
    path("manager/applications/<int:app_id>/approve/", views.mgr_approve, name="mgr_approve"),
    path("manager/applications/<int:app_id>/deny/", views.mgr_deny, name="mgr_deny"),
    path("manager/volunteers/", views.mgr_volunteers, name="mgr_volunteers"),
    path("manager/volunteers/import/", views.mgr_import_volunteers, name="mgr_import_volunteers"),
    path("manager/volunteers/<int:vol_id>/", views.mgr_volunteer_detail, name="mgr_volunteer_detail"),
    path("manager/volunteers/<int:vol_id>/toggle-active/", views.mgr_toggle_active, name="mgr_toggle_active"),
    path("manager/shifts/", views.mgr_shifts, name="mgr_shifts"),
    path("manager/shifts/create/", views.mgr_shift_create, name="mgr_shift_create"),
    path("manager/shifts/<int:shift_id>/", views.mgr_shift_detail, name="mgr_shift_detail"),
    path("manager/shifts/<int:shift_id>/edit/", views.mgr_shift_edit, name="mgr_shift_edit"),
    path("manager/shifts/<int:shift_id>/delete/", views.mgr_shift_delete, name="mgr_shift_delete"),
    path("manager/hours/", views.mgr_hour_logs, name="mgr_hour_logs"),
    path("manager/hours/<int:log_id>/delete/", views.mgr_hour_log_delete, name="mgr_hour_log_delete"),
    path("manager/email/", views.mgr_group_email, name="mgr_group_email"),
    path("manager/settings/", views.mgr_settings, name="mgr_settings"),
]
