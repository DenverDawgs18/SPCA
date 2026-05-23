from django.contrib import admin
from .models import Animal, ContactMessage


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ["name", "species", "breed", "gender", "status", "is_featured", "intake_date"]
    list_filter = ["species", "status", "is_featured", "gender"]
    search_fields = ["name", "breed", "description"]
    list_editable = ["status", "is_featured"]
    date_hierarchy = "intake_date"


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "subject", "created_at", "is_read"]
    list_filter = ["is_read"]
    search_fields = ["name", "email", "subject"]
    list_editable = ["is_read"]
    readonly_fields = ["created_at"]
