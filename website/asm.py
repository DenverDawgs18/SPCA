"""
ASM (Animal Shelter Manager) API wrapper.

All public methods return Python objects or raise ASMError.
Results are cached in Django's default cache for ASM_CACHE_SECONDS seconds.
"""

import logging
import urllib.parse
import urllib.request
import json

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

ASM_CACHE_SECONDS = 300  # 5 minutes


class ASMError(Exception):
    pass


def _get(method, **params):
    """Make an authenticated GET request to the ASM service API."""
    base_params = {
        "account": settings.ASM_ACCOUNT,
        "method": method,
    }
    if settings.ASM_API_USERNAME:
        base_params["username"] = settings.ASM_API_USERNAME
    if settings.ASM_API_PASSWORD:
        base_params["password"] = settings.ASM_API_PASSWORD
    base_params.update(params)
    url = f"{settings.ASM_API_URL}?{urllib.parse.urlencode(base_params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MedinaSPCA/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise ASMError(f"ASM HTTP {e.code}: {e.reason}")
    except Exception as e:
        raise ASMError(str(e))


def get_adoptable_animals():
    """
    Return list of adoptable animals from ASM.
    Each animal is a dict with keys: ANIMALID, ANIMALNAME, SPECIESNAME, BREEDNAME,
    SEXNAME, AGEGROUP, WEBSITEMEDIANAME, ANIMALCOMMENTS, etc.
    Returns [] if credentials are not set or API is unavailable.
    """
    if not settings.ASM_API_USERNAME:
        return []
    cache_key = f"asm_animals_{settings.ASM_ACCOUNT}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        raw = _get("online_get_adoptable_animals")
        animals = json.loads(raw)
        cache.set(cache_key, animals, ASM_CACHE_SECONDS)
        return animals
    except ASMError as e:
        logger.warning("ASM animals fetch failed: %s", e)
        return []
    except Exception as e:
        logger.warning("ASM animals parse failed: %s", e)
        return []


def animal_image_url(animal_id, seq=1):
    """Return a URL for an animal's photo served by ASM."""
    params = urllib.parse.urlencode({
        "account": settings.ASM_ACCOUNT,
        "method": "animal_image",
        "animalid": animal_id,
        "seq": seq,
    })
    return f"{settings.ASM_API_URL}?{params}"


def get_adoption_form_html():
    """Fetch the raw HTML of the ASM adoption application form."""
    if not settings.ASM_API_USERNAME:
        return None
    cache_key = f"asm_form_{settings.ASM_ACCOUNT}_{settings.ASM_ADOPTION_FORM_ID}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        raw = _get("online_form_html", formid=settings.ASM_ADOPTION_FORM_ID)
        html = raw.decode("utf-8", errors="replace")
        cache.set(cache_key, html, 3600)  # cache form 1 hour
        return html
    except ASMError as e:
        logger.warning("ASM form fetch failed: %s", e)
        return None


def submit_adoption_form(post_data: dict):
    """
    POST an adoption application to ASM.
    post_data should be a dict of field_name -> value matching the ASM form fields.
    Returns True on success, raises ASMError on failure.
    """
    params = {
        "account": settings.ASM_ACCOUNT,
        "method": "online_form_post",
        "formid": settings.ASM_ADOPTION_FORM_ID,
    }
    if settings.ASM_API_USERNAME:
        params["username"] = settings.ASM_API_USERNAME
    if settings.ASM_API_PASSWORD:
        params["password"] = settings.ASM_API_PASSWORD
    params.update(post_data)
    encoded = urllib.parse.urlencode(params).encode()
    try:
        req = urllib.request.Request(
            settings.ASM_API_URL,
            data=encoded,
            headers={"User-Agent": "MedinaSPCA/1.0", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201, 302)
    except Exception as e:
        raise ASMError(str(e))
