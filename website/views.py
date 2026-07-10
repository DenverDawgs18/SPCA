import json
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.conf import settings
from django.core.cache import cache
from .models import Animal, ContactMessage, NewsPost
from . import asm as asm_service


def health(request):
    return HttpResponse("ok")


def home(request):
    featured = Animal.objects.filter(status="available", is_featured=True)[:3]
    recent = Animal.objects.filter(status="available").exclude(is_featured=True)[:6]
    news = NewsPost.objects.filter(is_published=True)[:3]
    return render(request, "website/home.html", {
        "featured": featured,
        "recent": recent,
        "news": news,
    })


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
    return render(request, "website/donate.html", {
        "dp_form_id": settings.DONOR_PERFECT_FORM_ID,
        "dp_api_key": settings.DONOR_PERFECT_API_KEY,
        "zeffy_org_id": settings.ZEFFY_ORG_ID,
    })


def events(request):
    news = NewsPost.objects.filter(is_published=True)
    zeffy_org_id = settings.ZEFFY_ORG_ID
    return render(request, "website/events.html", {
        "news": news,
        "zeffy_org_id": zeffy_org_id,
    })


def about(request):
    return render(request, "website/about.html")


def faq(request):
    return render(request, "website/faq.html")


def microchipping(request):
    return render(request, "website/microchipping.html")


def report_cruelty(request):
    return render(request, "website/report_cruelty.html")


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


def api_animals(request):
    """Proxy ASM's adoptable animals as JSON for the frontend carousel."""
    animals = asm_service.get_adoptable_animals()
    # Normalize to a minimal shape the frontend expects
    result = []
    for a in animals:
        animal_id = a.get("ANIMALID") or a.get("ID", "")
        result.append({
            "id": animal_id,
            "name": a.get("ANIMALNAME", ""),
            "species": a.get("SPECIESNAME", ""),
            "breed": a.get("BREEDNAME", ""),
            "age": a.get("AGEGROUP", ""),
            "sex": a.get("SEXNAME", ""),
            "description": a.get("WEBSITEDESCRIPTION") or a.get("ANIMALCOMMENTS", ""),
            "image_url": asm_service.animal_image_url(animal_id) if animal_id else "",
        })
    return JsonResponse({"animals": result})


def adoption_application(request):
    """Custom-styled adoption application — submits to ASM on POST."""
    asm_configured = bool(settings.ASM_API_USERNAME)
    submitted = False
    error = None

    if request.method == "POST":
        # Collect form data
        post_data = {
            "firstname": request.POST.get("first_name", ""),
            "lastname": request.POST.get("last_name", ""),
            "emailaddress": request.POST.get("email", ""),
            "phoneNumber": request.POST.get("phone", ""),
            "address": request.POST.get("address", ""),
            "city": request.POST.get("city", ""),
            "state": request.POST.get("state", "OH"),
            "zipcode": request.POST.get("zip_code", ""),
            "animalname": request.POST.get("animal_name", ""),
            "livingsituation": request.POST.get("living_situation", ""),
            "ownrent": request.POST.get("own_rent", ""),
            "yardtype": request.POST.get("yard_type", ""),
            "otherpets": request.POST.get("other_pets", ""),
            "children": request.POST.get("children", ""),
            "previouspets": request.POST.get("previous_pets", ""),
            "whyadopt": request.POST.get("why_adopt", ""),
        }
        # Always save locally as a ContactMessage for backup
        ContactMessage.objects.create(
            name=f"{post_data['firstname']} {post_data['lastname']}",
            email=post_data["emailaddress"],
            phone=post_data["phoneNumber"],
            subject=f"Adoption Application — {post_data.get('animalname', 'General')}",
            message="\n".join(f"{k}: {v}" for k, v in post_data.items()),
        )
        # Submit to ASM if configured
        if asm_configured:
            try:
                asm_service.submit_adoption_form(post_data)
            except asm_service.ASMError as e:
                import logging
                logging.getLogger(__name__).warning("ASM form submit failed: %s", e)
                # Still treat as success — we saved locally
        submitted = True

    return render(request, "website/adoption_application.html", {
        "submitted": submitted,
        "asm_configured": asm_configured,
        "error": error,
    })
