from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("login/",    views.vol_login,    name="vol_login"),
    path("logout/",   views.vol_logout,   name="vol_logout"),
    path("register/", views.vol_register, name="vol_register"),

    # Volunteer portal
    path("",                views.vol_dashboard,    name="vol_dashboard"),
    path("profile/",        views.vol_profile,      name="vol_profile"),
    path("visits/",         views.vol_visit_history, name="vol_visit_history"),
    path("visits/log/",     views.vol_log_visit,    name="vol_log_visit"),

    # Manager portal
    path("manager/",                          views.mgr_dashboard,        name="mgr_dashboard"),
    path("manager/volunteers/",               views.mgr_volunteer_list,   name="mgr_volunteer_list"),
    path("manager/volunteers/<int:pk>/",      views.mgr_volunteer_detail, name="mgr_volunteer_detail"),
    path("manager/pending/",                  views.mgr_pending,          name="mgr_pending"),
    path("manager/settings/",                 views.mgr_settings,         name="mgr_settings"),
]
