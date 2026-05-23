# Deployment Guide — Medina County SPCA

Both the main website and the volunteer portal run as a single Django application on Fly.io with a managed Postgres database.

---

## Prerequisites

- [Fly.io account](https://fly.io/app/sign-up) (free tier works)
- [flyctl CLI](https://fly.io/docs/hands-on/install-flyctl/) installed
- Python 3.12+ and pip (for local dev)
- PostgreSQL (for local dev, optional; SQLite works fine locally)

---

## Local Development

### 1. Clone and set up the environment

```bash
git clone <repo-url>
cd SPCA
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
SECRET_KEY=any-long-random-string-for-local-dev
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

> **Note:** Leave `DATABASE_URL` as SQLite for local development. No Postgres installation needed.

### 3. Create the database tables

Migration files are already committed to the repo. Just run:

```bash
python manage.py migrate
```

This creates all tables including `volunteers_sitesettings`, `volunteers_volunteer`,
`volunteers_volunteervisit`, `website_animal`, and `website_contactmessage`.

> **Troubleshooting:** If you see an error like `no such table: volunteers_sitesettings`,
> it means migrations haven't been applied yet. Run `python manage.py migrate` and the
> error will go away. Do **not** run `makemigrations` unless you've changed a model.

### 4. Create a superuser (admin + volunteer manager)

```bash
python manage.py createsuperuser
```

This account gives you access to:
- Django admin at `/admin/` (manage animals, contact messages, volunteers)
- Volunteer manager portal at `/portal/manager/` (approve volunteers, view activity)

### 5. Initialize the inactivity settings

The volunteer inactivity rule (default: 2 visits / 90 days) is stored in the database.
It's created automatically the first time someone visits the manager portal, but you can
also seed it manually:

```bash
python manage.py shell -c "from volunteers.models import SiteSettings; SiteSettings.objects.get_or_create(pk=1)"
```

### 6. Start the dev server

```bash
python manage.py runserver
```

Visit:
- Main website: http://localhost:8000/
- Volunteer portal: http://localhost:8000/portal/
- Django admin: http://localhost:8000/admin/

---

## Fly.io Deployment

### 1. Log in to Fly

```bash
fly auth login
```

### 2. Edit fly.toml

Open `fly.toml` and change the `app` field to a unique name (must be globally unique on Fly.io):

```toml
app = "your-unique-app-name"
```

### 3. Launch the app (first time only)

```bash
fly launch --no-deploy
```

When prompted, choose **not** to overwrite `fly.toml` (you already have one).

### 4. Create the Postgres database

```bash
fly postgres create --name spca-db
fly postgres attach spca-db
```

This automatically sets the `DATABASE_URL` secret on your app.

### 5. Set required secrets

```bash
fly secrets set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(50))')"
fly secrets set DEBUG="False"
fly secrets set ALLOWED_HOSTS="your-unique-app-name.fly.dev"
```

### 6. Create a persistent volume for media uploads

```bash
fly volumes create spca_media --size 1 --region ord
```

### 7. Deploy

```bash
fly deploy
```

### 8. Run migrations on the remote instance

```bash
fly ssh console -C "python manage.py migrate"
```

### 9. Create the remote superuser

```bash
fly ssh console -C "python manage.py createsuperuser"
```

### 10. Verify

Visit `https://your-unique-app-name.fly.dev` — you should see the main website.

---

## Post-Deployment Setup

### Create the SiteSettings object (inactivity rule)

The volunteer inactivity threshold is stored in the database. After first deploy:

```bash
fly ssh console -C "python manage.py shell -c \"from volunteers.models import SiteSettings; SiteSettings.objects.get_or_create(pk=1)\""
```

Then visit `/portal/manager/settings/` to adjust the threshold (default: 2 visits / 90 days).

### Add animals to the site

Go to `/admin/` → Website → Animals → Add Animal.
- Upload a photo or paste an external photo URL.
- Check "Is featured" to show the animal on the homepage.

### Create volunteer manager accounts

Managers are Django staff users. To promote an existing user:

1. Go to `/admin/` → Auth → Users
2. Click the user → check "Staff status" → Save

Or create a new staff user directly in the admin.

---

## Updating the Site

```bash
# Make your changes locally, then:
fly deploy
fly ssh console -C "python manage.py migrate"   # only if models changed
```

---

## Domain (Custom URL)

To add a custom domain like `volunteers.medinacountyspca.com`:

```bash
fly certs add volunteers.medinacountyspca.com
```

Then add a CNAME record in your DNS pointing to `your-app-name.fly.dev`.
Also add the new domain to your `ALLOWED_HOSTS` secret.

---

## Costs

| Resource | Fly.io Free Tier |
|---|---|
| App (shared-cpu-1x, 256MB) | Free |
| Postgres (1GB) | ~$0/mo on free tier |
| Volume (1GB media) | ~$0.15/GB/mo |
| Outbound bandwidth | 100GB free/mo |

For a small nonprofit, costs should be near **$0–$3/month**.

---

## Architecture Summary

```
Browser
  │
  ▼
Fly.io (HTTPS)
  │
  ▼
Gunicorn (Django)
  ├── /               → Main website (website app)
  ├── /portal/        → Volunteer portal (volunteers app)
  ├── /admin/         → Django admin
  └── /static/        → WhiteNoise serves CSS/JS/images
         │
         ▼
    PostgreSQL (Fly.io managed)
    Volume mount at /app/media  (animal photos)
```
