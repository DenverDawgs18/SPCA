from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("", views.home, name="home"),
    path("adopt/", views.adopt, name="adopt"),
    path("adopt/apply/", views.adoption_application, name="adoption_application"),
    path("surrender/", views.surrender, name="surrender"),
    path("foster/", views.foster, name="foster"),
    path("volunteer/", views.volunteer_info, name="volunteer_info"),
    path("donate/", views.donate, name="donate"),
    path("events/", views.events, name="events"),
    path("about/", views.about, name="about"),
    path("faq/", views.faq, name="faq"),
    path("microchipping/", views.microchipping, name="microchipping"),
    path("report-cruelty/", views.report_cruelty, name="report_cruelty"),
    path("contact/", views.contact, name="contact"),
    path("api/animals/", views.api_animals, name="api_animals"),
]
