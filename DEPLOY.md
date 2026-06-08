# Deployment Guide — Medina County SPCA

The website runs as a single Django application on Fly.io with a managed Postgres database. It includes the full volunteer portal at `/portal/`.

---

## Prerequisites

- [Fly.io account](https://fly.io/app/sign-up) (free tier works)
- [flyctl CLI](https://fly.io/docs/hands-on/install-flyctl/) installed
- Python 3.12+ and pip (for local dev)

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

Edit `.env` — for local development these defaults are fine:

```
SECRET_KEY=any-long-random-string-for-local-dev
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

### 3. Create the database tables

Migration files are already committed. Just run:

```bash
python manage.py migrate
```

### 4. (Optional) Load sample animals

```bash
python manage.py loaddata sample_pets
```

This seeds 5 placeholder animals (Buddy, Luna, Max, Daisy, Oliver) so the homepage and adopt page are not empty on first run.

### 5. Create a superuser

```bash
python manage.py createsuperuser
```

Gives you access to `/admin/` to manage animals and contact messages.

### 6. Start the dev server

```bash
python manage.py runserver
```

Visit:
- Main website: http://localhost:8000/
- Django admin: http://localhost:8000/admin/

---

## Fly.io Deployment

### 1. Log in to Fly

```bash
fly auth login
```

### 2. Set your app name

Open `fly.toml` and change the `app` field to a name that's globally unique on Fly.io:

```toml
app = "your-unique-app-name"
```

### 3. Launch the app (first time only)

```bash
fly launch --no-deploy
```

When prompted, choose **not** to overwrite `fly.toml`.

### 4. Create the Postgres database

```bash
fly postgres create --name spca-db
fly postgres attach spca-db
```

This automatically sets `DATABASE_URL` as a secret on your app.

### 5. Set required secrets

```bash
fly secrets set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(50))')"
fly secrets set DEBUG="False"
fly secrets set ALLOWED_HOSTS="your-unique-app-name.fly.dev"
```

### 6. Create a persistent volume for media uploads

Animal photos uploaded through the admin are stored here.

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

### 10. (Optional) Load sample animals

```bash
fly ssh console -C "python manage.py loaddata sample_pets"
```

### 11. Verify

Visit `https://your-unique-app-name.fly.dev` — you should see the main website.

---

## Managing Animals

Go to `/admin/` → Website → Animals → Add Animal.

- Upload a photo or paste an external photo URL in the "Photo URL" field.
- Check **Is featured** to show the animal on the homepage (aim for 3 featured).
- The adopt page shows all animals with status "Available".

---

## Adding Real Images

Drop image files into `static/images/` matching the names in `static/images/IMAGES.txt`. No code changes are needed — the templates pick them up automatically.

The logo is the simplest example: drop `logo.svg` into `static/images/` and the navbar logo appears.

After adding images locally, run `python manage.py collectstatic` before deploying.

---

## Updating the Site

```bash
# Make your changes locally, then:
fly deploy
fly ssh console -C "python manage.py migrate"   # only if models changed
```

---

## Custom Domain

```bash
fly certs add medinacountyspca.com
fly certs add www.medinacountyspca.com
```

Add CNAME (or A/AAAA) records in your DNS pointing to your app. Also update `ALLOWED_HOSTS`:

```bash
fly secrets set ALLOWED_HOSTS="your-unique-app-name.fly.dev,medinacountyspca.com,www.medinacountyspca.com"
```

---

## Costs

| Resource | Fly.io Free Tier |
|---|---|
| App (shared-cpu-1x, 256 MB) | Free |
| Postgres (1 GB) | ~$0/mo on free tier |
| Volume (1 GB media) | ~$0.15/GB/mo |
| Outbound bandwidth | 100 GB free/mo |

For a small nonprofit, costs should be near **$0–$3/month**.

---

## Email Setup

The volunteer portal sends transactional emails (application confirmations, approvals, denials) and supports bulk volunteer emails from the manager portal.

### Local development

In development, emails are printed to the console (no SMTP needed):

```
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Production (Fly.io)

We recommend **SendGrid** (generous free tier) or **Gmail SMTP** with an App Password.

#### Option A — SendGrid

1. Create a free SendGrid account at sendgrid.com
2. Generate an API key with "Mail Send" permission
3. Set Fly secrets:

```bash
fly secrets set EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"
fly secrets set EMAIL_HOST="smtp.sendgrid.net"
fly secrets set EMAIL_PORT="587"
fly secrets set EMAIL_USE_TLS="True"
fly secrets set EMAIL_HOST_USER="apikey"
fly secrets set EMAIL_HOST_PASSWORD="<your-sendgrid-api-key>"
fly secrets set DEFAULT_FROM_EMAIL="Medina County SPCA <noreply@medinacountyspca.com>"
```

#### Option B — Gmail SMTP (App Password)

1. Enable 2-Step Verification on the Google account
2. Create an App Password at myaccount.google.com/apppasswords
3. Set Fly secrets:

```bash
fly secrets set EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"
fly secrets set EMAIL_HOST="smtp.gmail.com"
fly secrets set EMAIL_PORT="587"
fly secrets set EMAIL_USE_TLS="True"
fly secrets set EMAIL_HOST_USER="your-gmail@gmail.com"
fly secrets set EMAIL_HOST_PASSWORD="<your-app-password>"
fly secrets set DEFAULT_FROM_EMAIL="Medina County SPCA <your-gmail@gmail.com>"
```

---

## Architecture

```
Browser
  │
  ▼
Fly.io (HTTPS)
  │
  ▼
Gunicorn (Django)
  ├── /          → Main website (website app)
  ├── /portal/   → Volunteer portal (volunteers app)
  ├── /admin/    → Django admin
  └── /static/   → WhiteNoise serves CSS/JS/images
         │
         ▼
    PostgreSQL (Fly.io managed)
    Volume mount at /app/media  (uploaded animal photos)
```
