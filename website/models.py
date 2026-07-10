from django.db import models


class Animal(models.Model):
    SPECIES = [("dog", "Dog"), ("cat", "Cat"), ("other", "Other")]
    GENDERS = [("M", "Male"), ("F", "Female")]
    STATUS = [
        ("available", "Available"),
        ("pending", "Adoption Pending"),
        ("adopted", "Adopted"),
        ("hold", "On Hold"),
    ]

    name = models.CharField(max_length=100)
    species = models.CharField(max_length=20, choices=SPECIES)
    breed = models.CharField(max_length=100, blank=True)
    age_years = models.IntegerField(null=True, blank=True)
    age_months = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDERS)
    description = models.TextField()
    photo = models.ImageField(upload_to="animals/", blank=True)
    # Fallback if no uploaded photo — paste a direct image URL here
    photo_url = models.URLField(blank=True, help_text="External photo URL (used if no file uploaded)")
    status = models.CharField(max_length=20, choices=STATUS, default="available")
    intake_date = models.DateField()
    is_featured = models.BooleanField(default=False)
    is_good_with_kids = models.BooleanField(null=True, blank=True)
    is_good_with_dogs = models.BooleanField(null=True, blank=True)
    is_good_with_cats = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_featured", "-intake_date"]

    def __str__(self):
        return f"{self.name} ({self.get_species_display()})"

    def age_display(self):
        parts = []
        if self.age_years:
            parts.append(f"{self.age_years} yr{'s' if self.age_years != 1 else ''}")
        if self.age_months:
            parts.append(f"{self.age_months} mo")
        return " ".join(parts) if parts else "Age unknown"

    def photo_src(self):
        if self.photo:
            return self.photo.url
        if self.photo_url:
            return self.photo_url
        return None


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.subject}"


class NewsPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.TextField(help_text="Short preview shown on the homepage and listings.")
    body = models.TextField(help_text="Full article body. HTML allowed.")
    image_url = models.URLField(blank=True, help_text="Header image URL (optional).")
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "News Post"

    def __str__(self):
        return self.title
