from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Animal, ContactMessage


def home(request):
    featured = Animal.objects.filter(status="available", is_featured=True)[:3]
    recent = Animal.objects.filter(status="available").exclude(is_featured=True)[:6]
    return render(request, "website/home.html", {"featured": featured, "recent": recent})


def adopt(request):
    species = request.GET.get("species", "")
    animals = Animal.objects.filter(status="available")
    if species in ("dog", "cat", "other"):
        animals = animals.filter(species=species)
    return render(request, "website/adopt.html", {"animals": animals, "active_filter": species})


def surrender(request):
    return render(request, "website/surrender.html")


def foster(request):
    return render(request, "website/foster.html")


def volunteer_info(request):
    return render(request, "website/volunteer.html")


def donate(request):
    return render(request, "website/donate.html")


def about(request):
    return render(request, "website/about.html")


def faq(request):
    return render(request, "website/faq.html")


def contact(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()
        if name and email and subject and message:
            ContactMessage.objects.create(
                name=name, email=email, phone=phone, subject=subject, message=message
            )
            messages.success(request, "Thank you! We'll be in touch soon.")
            return redirect("contact")
        else:
            messages.error(request, "Please fill in all required fields.")
    return render(request, "website/contact.html")
