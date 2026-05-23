from django.contrib import admin
from .models import Volunteer, VolunteerVisit, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ["inactivity_days", "inactivity_min_visits"]

    def has_add_permission(self, request):
        # Only allow one settings row
        return not SiteSettings.objects.exists()


class VolunteerVisitInline(admin.TabularInline):
    model = VolunteerVisit
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ["__str__", "phone", "is_approved", "is_active_display", "last_visit_display", "created_at"]
    list_filter  = ["is_approved"]
    search_fields = ["user__first_name", "user__last_name", "user__email", "phone"]
    inlines = [VolunteerVisitInline]

    @admin.display(description="Active?", boolean=True)
    def is_active_display(self, obj):
        return obj.is_active()

    @admin.display(description="Last Visit")
    def last_visit_display(self, obj):
        v = obj.last_visit()
        return v.visit_date if v else "—"


@admin.register(VolunteerVisit)
class VolunteerVisitAdmin(admin.ModelAdmin):
    list_display = ["volunteer", "visit_date", "hours", "activity_type", "logged_by"]
    list_filter  = ["activity_type", "visit_date"]
    search_fields = ["volunteer__user__first_name", "volunteer__user__last_name"]
    date_hierarchy = "visit_date"
