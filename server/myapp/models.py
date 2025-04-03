from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError


class StartupIdea(models.Model):
    STAGE_CHOICES = [
        ("IDEA", "Idea Stage"),
        ("MVP", "MVP"),
        ("EARLY", "Early Stage"),
        ("GROWTH", "Growth Stage"),
        ("SCALING", "Scaling"),
    ]

    ROLE_CHOICES = [
        ("FOUNDER", "Founder"),
        ("CO_FOUNDER", "Co-Founder"),
        ("DEVELOPER", "Developer"),
        ("DESIGNER", "Designer"),
        ("MARKETER", "Marketing Specialist"),
        ("BUSINESS_DEV", "Business Developer"),
        ("PRODUCT_MANAGER", "Product Manager"),
        ("FINANCIAL_EXPERT", "Financial Expert"),
        ("OTHER", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="startup_ideas"
    )
    name = models.CharField(max_length=100)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default="IDEA")
    pitch = models.TextField(
        max_length=500, help_text="Elevator pitch for your startup idea"
    )
    description = models.TextField(help_text="Detailed description of your startup")
    looking_for = models.JSONField(
        default=list,
        help_text="Roles/skills you're looking for in potential co-founders",
    )
    skills = models.JSONField(
        default=list, help_text="List of skills and expertise needed for this idea"
    )
    pitch_deck = CloudinaryField(
        "pitch_deck",
        folder="startup_hub/pitch_decks",
        blank=True,
        null=True,
        resource_type="auto",
    )
    # User's role in this startup idea
    user_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="FOUNDER",
        help_text="Your role in this startup idea",
    )
    website = models.URLField(blank=True)
    funding_stage = models.CharField(max_length=100, blank=True)
    investment_needed = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Idea - {self.name}"

    class Meta:
        ordering = ["-created_at"]


class StartupImage(models.Model):
    startup_idea = models.ForeignKey(
        StartupIdea,
        on_delete=models.CASCADE,
        related_name="images",
        null=True,  # Make it nullable to allow migration
        blank=True,  # Allow blank in forms
    )
    image = CloudinaryField(
        "startup_image",
        folder="startup_hub/startup_images",
        transformation={"width": 800, "height": 600, "crop": "fill"},
    )
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.startup_idea:
            return f"Image for {self.startup_idea.name}"
        return "Startup Image"
