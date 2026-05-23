from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("adopt/", views.adopt, name="adopt"),
    path("surrender/", views.surrender, name="surrender"),
    path("foster/", views.foster, name="foster"),
    path("volunteer/", views.volunteer_info, name="volunteer_info"),
    path("donate/", views.donate, name="donate"),
    path("about/", views.about, name="about"),
    path("faq/", views.faq, name="faq"),
    path("microchipping/", views.microchipping, name="microchipping"),
    path("report-cruelty/", views.report_cruelty, name="report_cruelty"),
    path("contact/", views.contact, name="contact"),
]
