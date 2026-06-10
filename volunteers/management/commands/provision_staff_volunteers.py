from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Q

from volunteers.models import Volunteer


class Command(BaseCommand):
    help = "Create Volunteer profiles for any staff/superuser accounts that don't have one."

    def handle(self, *args, **options):
        staff = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True), is_active=True)

        created = 0
        for user in staff:
            _, made = Volunteer.objects.get_or_create(user=user)
            if made:
                self.stdout.write(
                    f"  Created: {user.get_full_name() or user.username} ({user.email})"
                )
                created += 1
            else:
                self.stdout.write(
                    f"  Skipped (already exists): {user.get_full_name() or user.username}"
                )

        self.stdout.write(self.style.SUCCESS(f"\nDone — {created} profile(s) created."))
