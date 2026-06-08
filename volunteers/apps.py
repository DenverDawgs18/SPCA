from django.apps import AppConfig


class VolunteersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "volunteers"
    verbose_name = "Volunteer Portal"

    def ready(self):
        import volunteers.signals  # noqa: F401
