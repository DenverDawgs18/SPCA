# Volunteer Portal — Archived

This directory contains a fully built volunteer management portal that was removed from the active deployment to simplify the initial site launch.

## What's here

- `volunteers/` — complete Django app (models, views, forms, URLs, templates, migrations)
- `static/css/volunteer.css` — portal stylesheet
- `static/js/volunteer.js` — sortable table + date helpers

## Re-integrating

To activate the portal again:

1. Copy `volunteers/` back to the project root.
2. Copy `static/css/volunteer.css` → `static/css/` and `static/js/volunteer.js` → `static/js/`.
3. In `spca_project/settings.py`, add `"volunteers"` to `INSTALLED_APPS` and restore:
   ```python
   LOGIN_URL = "/portal/login/"
   LOGIN_REDIRECT_URL = "/portal/"
   LOGOUT_REDIRECT_URL = "/"
   ```
4. In `spca_project/urls.py`, add:
   ```python
   path("portal/", include("volunteers.urls")),
   ```
5. Run `python manage.py migrate`.
6. Update the volunteer page (`website/templates/website/volunteer.html`) to re-add the portal CTA buttons:
   ```html
   <a href="/portal/register/" class="btn btn-navy btn-lg">Create an Account</a>
   <a href="/portal/login/" class="btn btn-outline btn-lg">Already a Volunteer? Log In</a>
   ```

## Features

- Self-register + manager approval flow
- Visit logging (date, hours, activity type, notes)
- Inactivity rule: configurable threshold (default 2 visits / 90 days), editable at `/portal/manager/settings/`
- Manager views: approve/deny, volunteer list with active/inactive filter, private notes
- Django `is_staff` flag gates manager access
